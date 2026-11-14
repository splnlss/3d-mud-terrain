"""Relief-style 3D Tiles for the whole region: a quadtree of clay-model tiles with geographic coordinates.

Each tile is authored as its own 1.6 m clay model of its ground square, so every zoom level
reads as a sculpted relief. Tiles are authored with a halo on world-anchored noise, so
neighbours at the same level agree along their shared edge.

    uv run python -m bake.style.relief_tiles --output data/relief-tiles --levels 0-4
    uv run python -m bake.style.relief_tiles --output data/relief-tiles --refine -105.27,37.18,2 --levels 5-6
    uv run python -m bake.style.relief_tiles --output data/relief-tiles --tileset
"""
import argparse
import hashlib
import io
import json
import struct
import subprocess
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from urllib.request import urlopen
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import transform
from rasterio.windows import Window
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, uniform_filter, zoom
from scipy.spatial import cKDTree
from PIL import Image
from bake.tooling import ktx_tool
from bake.style.fields import NAIP, field_parcels
from bake.style.region_sources import load_sources, region_frame, region_pivots
from bake.style.relief_patch import densify, tilled_ground
from bake.style.relief_study import LATTICE_DEVIATION, Fields, hashed_normal, mound_field, smoothstep, style_surface

DEM = 'data/san-luis-112640-10.tif'; HYDRO = 'data/nhd-112640.json'
CORE = 1537; HALO = 72; MESH_STEP = 8; SPAN = 1.6; SEED = 404; TEXTURE = 1536
# One vertical exaggeration for every landform and every level, so peaks, ridges and fans keep their true proportions.
GAIN = 1.25
HOME_HEIGHT_M = 4.5; BED_DEPTH_M = 1.2
SNOW_LINE_M = (3650, 4050)
# Sculpted canopy: trees and brush are pressed-on clay lumps. Sizes are ground metres, anchored to the ground,
# so every level shows the same lumps; a coarse mesh simply carries fewer of the small ones.
LUMP_WAVELENGTHS_M = (560, 280, 140, 70, 35, 16, 7); LUMP_HEIGHT = (.05, .05, .05, .035, .028, .028, .028); CANOPY_LIFT_M = 9; OPEN_GROUND_SHARE = .2   # true elevation where snow starts and where it is complete
IMAGE_PX = 1100          # imagery samples across the tile core
BASE_M = 2200.0          # below the lowest ground in the region: model zero and the base of vertical exaggeration
GEOID_M = -16.2          # ellipsoid minus NAVD88 here, measured against Google 3D Tiles on the Culebra tile
NORMAL_SCALE = .6        # the clay was tuned under soft global light; real-time direct light needs gentler detail normals
from bake.style.water_palette import WATER_LINEAR, WATER_ROUGHNESS
ROAD_LEVEL = {'motorway': 0, 'trunk': 0, 'primary': 0, 'secondary': 0, 'tertiary': 2, 'unclassified': 3, 'residential': 3, 'service': 5, 'track': 5}


def tile_square(frame, level, ix, iy):
    _, west, north, size = frame; side = size / 2 ** level
    return west + ix * side, north - iy * side, side


def fetch_imagery(work, crs, west, north, side, level, ix, iy):
    """NAIP true colour and colour-infrared for the tile plus halo, cached per tile."""
    pad = side * HALO / (CORE - 1); pixels = round(IMAGE_PX * (CORE - 1 + 2 * HALO) / (CORE - 1)); epsg = crs.split(':')[1]
    box = f'{west - pad},{north - side - pad},{west + side + pad},{north + pad}'; out = []
    for name, bands, kind in [('rgb', '0,1,2', 'jpg'), ('cir', '3,0,1', 'png')]:
        path = Path(work) / 'imagery' / f'{level}-{ix}-{iy}-{name}.{kind}'; path.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(10):
            if path.exists(): break
            try:
                data = urlopen(f'{NAIP}?bbox={box}&bboxSR={epsg}&imageSR={epsg}&size={pixels},{pixels}&format={kind}&bandIds={bands}&f=image', timeout=240).read()
                if data[:1] != b'<' and data[:1] != b'{': path.write_bytes(data)
            except OSError: pass
            if not path.exists(): time.sleep(8 * (attempt + 1))
        if not path.exists(): raise RuntimeError(f'NAIP imagery unavailable for tile {level}/{ix}/{iy}')
        out.append(np.asarray(Image.open(path).convert('RGB'), float))
    # NAIP is flown state by state: New Mexico imagery (south of 37 N) is matched to Colorado's tone.
    match = border_match(work, crs)
    if match is not None:
        rows = north + pad - (np.arange(out[0].shape[0]) + .5) * (side + 2 * pad) / out[0].shape[0]
        south = np.interp(rows, [match['northing'] - 150, match['northing'] + 150], [1, 0])[:, None, None]
        out = [np.clip(image * (1 - south) + (image * match['gain'][i] + match['offset'][i]) * south, 0, 255) for i, image in enumerate(out)]
    return out


def border_match(work, crs):
    """Per-band gain and offset mapping imagery just south of the state line onto imagery just north of it."""
    path = Path(work) / 'border-match.json'
    if path.exists(): return json.loads(path.read_text()) or None
    root = [Path(work) / 'imagery' / f'0-0-0-{name}' for name in ('rgb.jpg', 'cir.png')]
    if not all(p.exists() for p in root): return None  # the root tile is baked first and writes this file
    _, west, north, size = region_frame(DEM); _, northing = transform('EPSG:4326', crs, [-105.5], [37.0]); northing = northing[0]
    result = {'northing': northing, 'gain': [], 'offset': []}
    for p in root:
        image = np.asarray(Image.open(p).convert('RGB'), float); pad = size * HALO / (CORE - 1); metres = (size + 2 * pad) / image.shape[0]
        row = int((north + pad - northing) / metres); band = int(4000 / metres)
        above, below = image[row - band:row - 2].reshape(-1, 3), image[row + 2:row + band].reshape(-1, 3)
        gain = above.std(0) / below.std(0); result['gain'].append(gain.tolist()); result['offset'].append((above.mean(0) - gain * below.mean(0)).tolist())
    path.write_text(json.dumps(result)); return result


def exaggerate(ground):
    """Displayed elevation from true elevation."""
    return BASE_M + GAIN * (ground - BASE_M)


def world_noise(frame, x, y, wavelength_m, salt):
    """Unit-deviation noise fixed to the ground: the same value at a place whatever tile or level asks."""
    _, west, north, _ = frame; step = wavelength_m / 3; u = (x - west) / step; v = (north - y) / step
    c0, r0 = int(np.floor(u.min())) - 8, int(np.floor(v.min())) - 8
    iy, ix = np.mgrid[r0:int(np.ceil(v.max())) + 9, c0:int(np.ceil(u.max())) + 9]
    lattice = gaussian_filter(hashed_normal(ix + 10 ** 6, iy + 10 ** 6, salt), 1.5)
    return (map_coordinates(lattice, [v - r0, u - c0], order=3) / LATTICE_DEVIATION).astype('float32')


def canopy_lumps(frame, x, y, cover, finest_m):
    """Raised lumps in displayed metres for woody `cover` (0..1), using only lump sizes of at least `finest_m`."""
    total = CANOPY_LIFT_M * cover
    for i, wavelength in enumerate(LUMP_WAVELENGTHS_M):
        if wavelength < finest_m: continue
        knob = np.clip(world_noise(frame, x, y, wavelength, 9000 + i) + .35, 0, 2.2)  # mostly bumps, few hollows
        total = total + LUMP_HEIGHT[i] * wavelength * knob * (OPEN_GROUND_SHARE + (1 - OPEN_GROUND_SHARE) * cover)
    return total


def read_ground(west, north, side, x, y, cell_m):
    """Bare-earth elevation at grid points, from the regional DEM averaged to about `cell_m`."""
    with rasterio.open(DEM) as src:
        res = src.res[0]; pad = side * .08
        c0 = int(np.floor((x.min() - pad - src.bounds.left) / res)); c1 = int(np.ceil((x.max() + pad - src.bounds.left) / res))
        r0 = int(np.floor((src.bounds.top - y.max() - pad) / res)); r1 = int(np.ceil((src.bounds.top - y.min() + pad) / res))
        c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, src.width), min(r1, src.height)
        factor = max(1, int(cell_m / res)); shape = (max(2, (r1 - r0) // factor), max(2, (c1 - c0) // factor))
        data = src.read(1, window=Window(c0, r0, c1 - c0, r1 - r0), out_shape=shape, resampling=Resampling.average)
        cols = ((x - src.bounds.left) / res - c0) / (c1 - c0) * shape[1] - .5; rows = ((src.bounds.top - y) / res - r0) / (r1 - r0) * shape[0] - .5
    return map_coordinates(data.astype('float32'), [rows, cols], order=1, mode='nearest')


def coarse_cover(rgb, cir, px_m):
    """Woody cover and farmland 0..1 from imagery, by a rule that holds from 1 m to 100 m pixels."""
    nir, red = cir[..., 0], cir[..., 1]; ndvi = (nir - red) / (nir + red + 1e-6); lum = rgb.mean(2)
    green = smoothstep(gaussian_filter(ndvi, 1), .12, .34)
    if px_m < 3:
        grey = cir.mean(2); rough = np.sqrt(np.clip(uniform_filter(grey ** 2, 7) - uniform_filter(grey, 7) ** 2, 0, None))
        return green * smoothstep(gaussian_filter(rough, 2), 11, 24), lum
    # At coarse pixels texture is gone: trees and brush are green in infrared and dark in visible light, crops are bright.
    return green * (1 - smoothstep(gaussian_filter(lum, 1), 62, 100)), lum


def author_tile(sources, frame, work, level, ix, iy):
    crs = frame[0]; west, north, side = tile_square(frame, level, ix, iy); n = CORE + 2 * HALO; px_m = side / (CORE - 1)
    f = Fields(n, SPAN * (n - 1) / (CORE - 1), SEED + level, origin=(ix * (CORE - 1) - HALO, iy * (CORE - 1) - HALO))
    scale = SPAN / side; mm = .001 / scale  # one model millimetre in ground metres
    x, y = np.meshgrid(west + (np.arange(n) - HALO) * px_m, north - (np.arange(n) - HALO) * px_m)
    ground = read_ground(west, north, side, x, y, max(10, px_m)); base = sources['base_elevation_m']
    if 12 / px_m > .6: ground = gaussian_filter(ground, 12 / px_m)  # DEM seams and terrace edges
    true_ground = ground; ground = exaggerate(ground)  # everything below works in displayed metres
    # The mesh carries only this terrain, sampled the same way at every level, so levels agree and no peak is invented.
    nodes = np.arange(HALO, HALO + CORE, MESH_STEP)
    mesh = exaggerate(read_ground(west, north, side, x[np.ix_(nodes, nodes)], y[np.ix_(nodes, nodes)], max(10, px_m * MESH_STEP / 2)))
    plain = ground
    lo_x, hi_x, lo_y, hi_y = x.min() - 60 * mm, x.max() + 60 * mm, y.min() - 60 * mm, y.max() + 60 * mm
    inside = lambda xy: (xy[:, 0].max() > lo_x) & (xy[:, 0].min() < hi_x) & (xy[:, 1].max() > lo_y) & (xy[:, 1].min() < hi_y)

    # Rivers, streams and canals: fewer at overview levels, each at least wide enough to read.
    visible = side / SPAN * 6; points = []  # NHD marks each line with the smallest map scale that should show it
    for line in sources['lines']:
        if line['visibility'] < visible and level < 5: continue
        if line['ftype'] == 336 and level < 3: continue
        if not inside(line['xy']): continue
        real, least = (16, 3.6) if line['visibility'] >= 1000000 else (8, 2.2) if line['visibility'] >= 250000 else (4, 1.4)
        if line['ftype'] == 336: real, least = 3, 1.0
        p = densify(line['xy'], px_m * .75); points.append(np.column_stack([p, np.full(len(p), max(real, least * mm))]))
    flow = np.full((n, n), 1.0, 'float32'); level_at = ground.copy(); grid_pts = np.column_stack([x.ravel(), y.ravel()])
    sample = lambda array, px, py: map_coordinates(array, [(north - py) / px_m + HALO, (px - west) / px_m + HALO], order=1, mode='nearest')
    valley = gaussian_filter(ground, max(15 / px_m, 1.0))
    if points:
        points = np.concatenate(points); dist, ids = cKDTree(points[:, :2]).query(grid_pts, workers=-1)
        flow = ((dist - points[ids, 2]) * scale).reshape(n, n).astype('float32')
        level_at = sample(valley, points[:, 0], points[:, 1])[ids].reshape(n, n)
    lakes = [lake['polygon'] for lake in sources['lakes'] if lake['area_m2'] > (2.5 * mm) ** 2
             and lake['bounds'][2] > lo_x and lake['bounds'][0] < hi_x and lake['bounds'][3] > lo_y and lake['bounds'][1] < hi_y]
    if lakes:
        wet = rasterize([(lake, 1) for lake in lakes], out_shape=(n, n), transform=from_origin(x[0, 0] - px_m / 2, y[0, 0] + px_m / 2, px_m, px_m)).astype(bool)
        if wet.any():
            outside, nearest = distance_transform_edt(~wet, return_indices=True); within = distance_transform_edt(wet)
            lake_flow = np.where(wet, -within, outside) * px_m * scale; closer = lake_flow < flow
            flow = np.where(closer, lake_flow, flow).astype('float32'); level_at = np.where(closer, valley[tuple(nearest)], level_at)
    flow = gaussian_filter(flow, .0012 / f.px); bank = flow + .0009 * f.noise(.03) + .0004 * f.noise(.012)
    # Land is measured above the nearest water level, never below the ground itself.
    surface = gaussian_filter(np.minimum(level_at, gaussian_filter(ground, .02 / f.px)), .03 / f.px)
    above = np.clip(ground - surface, 0, None) * scale
    rgb, cir = fetch_imagery(work, crs, west, north, side, level, ix, iy); image_m = (n - 1) * px_m / (rgb.shape[0] - 1)
    woody, lum = coarse_cover(rgb, cir, image_m)
    dark = 1 - np.clip((lum - 45) / (150 - 45), 0, 1)  # fixed levels: every tile reads tone the same way
    shade_image = np.maximum(dark ** 1.3, .95 * woody)
    shade_image = gaussian_filter(shade_image, max(3 / image_m, .6))
    ratio = (rgb.shape[0] - 1) / (n - 1); rows, cols = np.mgrid[0:n, 0:n] * ratio; nudge = 1.5 / image_m
    shade = map_coordinates(shade_image, [rows + nudge * f.noise(.02), cols + nudge * f.noise(.02)], order=1, mode='nearest').astype('float32')
    # Rectangular parcels are read from imagery once pixels are fine enough; centre pivots come from the regional list at every level.
    tilled, parcels = tilled_ground(f, cir if image_m <= 8 else np.zeros_like(cir), (n - 1) * px_m, row_spacing_m=max(7.5, 5 * mm), pixel_m=image_m)
    pivots = sources['pivots']; pivots = pivots[(pivots[:, 0] > lo_x) & (pivots[:, 0] < hi_x) & (pivots[:, 1] > lo_y) & (pivots[:, 1] < hi_y)]
    for px_, py_, radius, tone in pivots:
        c, r = (px_ - x[0, 0]) / px_m, (y[0, 0] - py_) / px_m; k = int(radius / px_m) + 4
        r0, r1, c0, c1 = max(int(r) - k, 0), min(int(r) + k + 1, n), max(int(c) - k, 0), min(int(c) + k + 1, n)
        if r0 >= r1 or c0 >= c1: continue
        yy, xx = np.mgrid[r0:r1, c0:c1]; d = np.hypot(xx - c, yy - r) * px_m; disc = 1 - smoothstep(d, radius - 1.2 * mm, radius)
        box = (slice(r0, r1), slice(c0, c1)); on = disc > tilled['mask'][box]
        tilled['mask'][box] = np.maximum(tilled['mask'][box], disc)
        tilled['rows'][box] = np.where(on, np.sin(2 * np.pi * d / max(7.5, 5 * mm)), tilled['rows'][box])
        tilled['tone'][box] = np.where(on, np.clip((tone * 255 - 90) / 80, 0, 1), tilled['tone'][box])
        tilled['edge'][box] = np.maximum(tilled['edge'][box], np.exp(-((d - radius) / (.8 * mm)) ** 2) * .8)
    # Fields exist only on gentle ground; bright alpine meadows on mountain slopes are not farmland.
    gy, gx = np.gradient(gaussian_filter(true_ground, max(40 / px_m, 1)), px_m); gentle = 1 - smoothstep(np.hypot(gx, gy), .05, .1)
    tilled['mask'] = (tilled['mask'] * smoothstep(bank, .006, .02) * gentle).astype('float32'); tilled['edge'] *= tilled['mask'] > .02

    roads = [(road['xy'], max(3.5 if road['highway'] in ('track', 'service') else 4.5, (2.4 if ROAD_LEVEL[road['highway']] == 0 else 1.6) * mm))
             for road in sources['roads'] if ROAD_LEVEL[road['highway']] <= level and inside(road['xy'])]
    wobble = .0006 * f.noise(.03); tracks = np.zeros((n, n), 'float32')
    if roads:
        pts = np.concatenate([np.column_stack([densify(xy, px_m * .75), np.full(len(densify(xy, px_m * .75)), half)]) for xy, half in roads])
        dist, ids = cKDTree(pts[:, :2]).query(grid_pts, workers=-1)
        tracks = (1 - smoothstep(((dist - pts[ids, 2]) * scale).reshape(n, n) + wobble, -.0005, .0012)).astype('float32') * smoothstep(bank, .0, .0015)
    blocks = np.zeros((n, n), 'float32'); homes = sources['buildings']
    homes = homes[(homes[:, 0] > lo_x) & (homes[:, 0] < hi_x) & (homes[:, 1] > lo_y) & (homes[:, 1] < hi_y)] if level >= 2 else homes[:0]
    if len(homes):
        dist, _ = cKDTree(homes).query(grid_pts, workers=-1, distance_upper_bound=20 * mm)
        blocks = (1 - smoothstep((np.minimum(dist, 1e9) - max(7, .8 * mm)) * scale, 0, .0005)).reshape(n, n).astype('float32') * smoothstep(bank, 0, .002) * (1 - tracks)
    # Lumps sit on trees and brush, faintly on open wild ground, never on water, fields, roads or buildings.
    cover = map_coordinates(woody, [rows, cols], order=1, mode='nearest') * smoothstep(bank, .0, .003) * (1 - tilled['mask']) * (1 - tracks) * (1 - blocks)
    open_ground = smoothstep(bank, .0, .003) * (1 - tilled['mask']) * (1 - tracks) * (1 - blocks)
    # Lumps smaller than three samples cannot be drawn at this level, and their lattice would be enormous on a coarse tile.
    lumps = canopy_lumps(frame, x, y, cover, 3 * px_m) * open_ground
    spacing = px_m * MESH_STEP
    mesh = mesh + (canopy_lumps(frame, x, y, cover, 4 * spacing) * open_ground)[np.ix_(nodes, nodes)]
    # Real-size features the mesh can carry once tiles are fine enough to walk through: stream beds dip, buildings stand.
    if spacing < 12:
        mesh = mesh + (HOME_HEIGHT_M * blocks - BED_DEPTH_M * smoothstep(-bank, -.0006, .0012))[np.ix_(nodes, nodes)]
    land = above + lumps * scale + .004
    maps = style_surface(f, land.astype('float32'), bank, flow, ((surface - base) * scale).astype('float32'), tilled, shade, tracks, blocks, true_terrain=True)
    # Snow on high ground, thinner on steep faces, with a ragged lower edge.
    gy, gx = np.gradient(true_ground, px_m); steep = smoothstep(np.hypot(gx, gy), .5, 1.1)
    snow = smoothstep(true_ground + 110 * f.noise(.05) + 50 * f.noise(.012), *SNOW_LINE_M) * (1 - .55 * steep) * (1 - maps['channel'])
    maps['base_color'] = maps['base_color'] * (1 - .88 * snow[..., None]) + np.array([.72, .72, .70], 'float32') * .88 * snow[..., None]
    maps['roughness'] = (maps['roughness'] * (1 - snow) + .62 * snow).astype('float32')
    gz, gx = np.gradient(gaussian_filter(flow, .002 / f.px)); dz, dx = np.gradient(gaussian_filter(surface, .02 / f.px))
    tx, tz = -gz, gx; sign = np.where(tx * -dx + tz * -dz >= 0, 1, -1); norm = np.hypot(tx, tz) + 1e-9
    maps['flow_dir'] = np.dstack([sign * tx / norm, sign * tz / norm]).astype('float32')
    core = slice(HALO, HALO + CORE)
    out = {key: value[core, core] for key, value in maps.items()}
    out['elevation'] = base + out.pop('height') / scale  # sculpted surface in displayed metres; shading only
    out['mesh'] = mesh
    return out, {'parcels': len(parcels), 'pivots': int(len(pivots)), 'roads': len(roads), 'buildings': int(len(homes)), 'lakes': len(lakes)}


def enu_frame(crs, x, y, h):
    """ECEF position of a point and the east, north, up axes there."""
    lon, lat = transform(crs, 'EPSG:4326', [x], [y]); lon, lat = np.radians(lon[0]), np.radians(lat[0])
    centre = np.array([v[0] for v in transform('EPSG:4979', 'EPSG:4978', [np.degrees(lon)], [np.degrees(lat)], [h])])
    east = np.array([-np.sin(lon), np.cos(lon), 0]); up = np.array([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    return centre, east, np.cross(up, east), up


def to_srgb(c):
    return np.where(c <= .0031308, 12.92 * c, 1.055 * np.clip(c, 1e-9, None) ** (1 / 2.4) - .055)


def ktx_bytes(array, *options):
    """KTX2 with mipmaps via toktx; power-of-two input."""
    executable, _ = ktx_tool()
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / 'in.png', Path(folder) / 'out.ktx2'; Image.fromarray(array).save(source, compress_level=1)
        subprocess.run([executable, '--t2', '--genmipmap', '--threads', '2', *options, str(target), str(source)], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return target.read_bytes()


ETC1S = ('--encode', 'etc1s', '--clevel', '2', '--qlevel', '200'); UASTC = ('--encode', 'uastc', '--uastc_quality', '2', '--uastc_rdo_l', '3.0', '--zcmp', '12')


def root_frame(frame):
    """The tileset's single local frame: east/north/up at the region centre, on the exaggeration base height."""
    crs, west, north, size = frame
    return enu_frame(crs, west + size / 2, north - size / 2, BASE_M + GEOID_M)


def write_glb(path, maps, frame, level, ix, iy):
    """One tile as a GLB in the tileset's east-up-south frame, plus its bounding box in east-north-up."""
    crs = frame[0]; west, north, side = tile_square(frame, level, ix, iy); px_m = side / (CORE - 1)
    elevation = maps['elevation'].astype('float64') + GEOID_M; nodes = np.arange(0, CORE, MESH_STEP); m = len(nodes)
    gx, gy = np.meshgrid(west + nodes * px_m, north - nodes * px_m); height = maps['mesh'].astype('float64') + GEOID_M
    lon, lat = transform(crs, 'EPSG:4326', gx.ravel(), gy.ravel())
    ecef = np.column_stack(transform('EPSG:4979', 'EPSG:4978', lon, lat, height.ravel()))
    centre, east, north_axis, up = root_frame(frame)
    local = ecef - centre; e, nn, u = local @ east, local @ north_axis, local @ up
    position = np.column_stack([e, u, -nn]).reshape(m, m, 3)  # glTF y-up; 3D Tiles turns it to z-up before the transform
    d_col = np.gradient(position, axis=1); d_row = np.gradient(position, axis=0)
    normal = np.cross(d_row, d_col); normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    tangent = d_col - normal * (d_col * normal).sum(2, keepdims=True); tangent /= np.linalg.norm(tangent, axis=2, keepdims=True)
    uv = np.stack(np.meshgrid((nodes + .5) / TEXTURE, (nodes + .5) / TEXTURE), -1)  # textures drop the last row and column; the edge clamps
    index = np.arange(m * m).reshape(m, m)
    quads = np.stack([index[:-1, :-1], index[1:, :-1], index[:-1, 1:], index[:-1, 1:], index[1:, :-1], index[1:, 1:]], -1).reshape(-1, 3)
    # A skirt hangs from the edge so neighbouring levels never show a gap.
    ring = np.concatenate([index[0, :], index[:, -1], index[-1, ::-1], index[::-1, 0]]); drop = side / 40
    flat = lambda a: a.reshape(-1, a.shape[-1])
    skirt_pos = flat(position)[ring] - np.array([0, drop, 0]); k = len(ring); base_id = m * m
    a, b = ring, np.roll(ring, -1); sa, sb = base_id + np.arange(k), base_id + np.roll(np.arange(k), -1)
    skirt = np.concatenate([np.column_stack([a, sa, b]), np.column_stack([b, sa, sb])])
    # Positions stay float32; normals, tangents and texture coordinates are quantised (KHR_mesh_quantization).
    vertices = np.concatenate([flat(position), skirt_pos]).astype('float32')
    pack = lambda a: np.clip(np.rint(a * 127), -127, 127).astype('int8')
    normals = pack(np.column_stack([np.concatenate([flat(normal), flat(normal)[ring]]), np.zeros(len(vertices))]))  # padded to four bytes
    tangents = np.concatenate([flat(tangent), flat(tangent)[ring]]); tangents = pack(np.column_stack([tangents, np.ones(len(tangents))]))
    uvs = np.rint(np.clip(np.concatenate([flat(uv), flat(uv)[ring]]), 0, 1) * 65535).astype('uint16'); triangles = np.concatenate([quads, skirt]).astype('uint16')

    # Detail the mesh cannot carry goes into a tangent-space normal map (glTF: +X east, +Y north, +Z out).
    coarse = map_coordinates(height, np.mgrid[0:CORE, 0:CORE] / MESH_STEP, order=1)
    d_row_r, d_col_r = np.gradient(elevation - coarse, px_m)
    detail = np.dstack([-d_col_r, d_row_r, np.ones_like(d_col_r)]); detail /= np.linalg.norm(detail, axis=2, keepdims=True)
    water = maps['channel'][..., None]
    colour = maps['base_color'] * (1 - water) + np.array(WATER_LINEAR) * water
    rough = maps['roughness'] * (1 - water[..., 0]) + WATER_ROUGHNESS * water[..., 0]
    byte = lambda a: np.uint8(np.clip(a, 0, 1) * 255 + .5)[:TEXTURE, :TEXTURE]
    images = [ktx_bytes(byte(to_srgb(colour)), '--assign_oetf', 'srgb', *ETC1S),
              ktx_bytes(byte(detail * .5 + .5), '--assign_oetf', 'linear', *UASTC),
              ktx_bytes(byte(np.dstack([np.ones_like(rough), rough, np.zeros_like(rough)])), '--assign_oetf', 'linear', *ETC1S)]
    # Shader inputs stay outside the GLB so viewers that do not use them never load them.
    stem = Path(path).with_suffix('')
    Image.fromarray(byte(np.dstack([maps['channel'], np.clip(-maps['bank'] / .01, 0, 1), maps['road']]))).save(f'{stem}-water.png', compress_level=6)
    Image.fromarray(byte(np.dstack([maps['flow_dir'] * (maps['bank'] < .004)[..., None] * .5 + .5, np.zeros_like(rough)]))).save(f'{stem}-flow.png', compress_level=6)
    chunks, views = [], []

    def add(data, target=None):
        offset = sum(len(c) for c in chunks); chunks.append(data + b'\0' * (-len(data) % 4))
        views.append({'buffer': 0, 'byteOffset': offset, 'byteLength': len(data), **({'target': target} if target else {})}); return len(views) - 1

    accessors = []
    for data, kind, component in [(vertices, 'VEC3', 5126), (normals, 'VEC3', 5120), (tangents, 'VEC4', 5120), (uvs, 'VEC2', 5123), (triangles.ravel(), 'SCALAR', 5123)]:
        accessor = {'bufferView': add(data.tobytes(), 34963 if kind == 'SCALAR' else 34962), 'componentType': component, 'count': len(data), 'type': kind}
        if component in (5120, 5123) and kind != 'SCALAR': accessor['normalized'] = True
        if data is normals: views[-1]['byteStride'] = 4
        if data is vertices: accessor.update(min=vertices.min(0).tolist(), max=vertices.max(0).tolist())
        accessors.append(accessor)
    gltf = {'asset': {'version': '2.0', 'generator': 'san-luis-relief bake.style.relief_tiles'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
        'nodes': [{'mesh': 0, 'name': f'relief {level}/{ix}/{iy}'}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0, 'NORMAL': 1, 'TANGENT': 2, 'TEXCOORD_0': 3}, 'indices': 4, 'material': 0}]}],
        'materials': [{'name': 'Relief clay', 'doubleSided': True, 'pbrMetallicRoughness': {'baseColorTexture': {'index': 0}, 'metallicRoughnessTexture': {'index': 2}, 'metallicFactor': 0},
            'normalTexture': {'index': 1, 'scale': NORMAL_SCALE},
            'extras': {'waterMap': f'{stem.name}-water.png', 'waterMapChannels': 'R water mask, G bank distance (0 edge .. 1 at 10 model mm), B road',
                'flowMap': f'{stem.name}-flow.png', 'flowMapChannels': 'RG downstream unit vector, +R east, +G south, 0.5 = zero', 'waterColorLinear': WATER_LINEAR, 'waterRoughness': WATER_ROUGHNESS}}],
        'samplers': [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071}],
        'extensionsUsed': ['KHR_texture_basisu', 'KHR_mesh_quantization'], 'extensionsRequired': ['KHR_texture_basisu', 'KHR_mesh_quantization'],
        'textures': [{'sampler': 0, 'extensions': {'KHR_texture_basisu': {'source': i}}} for i in range(len(images))],
        'images': [{'mimeType': 'image/ktx2', 'bufferView': add(data)} for data in images],
        'accessors': accessors}
    gltf['bufferViews'] = views; binary = b''.join(chunks); gltf['buffers'] = [{'byteLength': len(binary)}]
    text = json.dumps(gltf, separators=(',', ':')).encode(); text += b' ' * (-len(text) % 4)
    Path(path).write_bytes(struct.pack('<III', 0x46546C67, 2, 28 + len(text) + len(binary)) + struct.pack('<II', len(text), 0x4E4F534A) + text
                           + struct.pack('<II', len(binary), 0x004E4942) + binary)
    # Bounding box in the tileset frame (east, north, up): centre, then the three half-axes.
    lo = np.array([e.min(), nn.min(), u.min() - drop]); hi = np.array([e.max(), nn.max(), u.max() + 30])
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    lon, lat = np.radians(lon), np.radians(lat)
    return {'box': [float(v) for v in [*mid, half[0], 0, 0, 0, half[1], 0, 0, 0, half[2]]],
        'region': [float(lon.min()), float(lat.min()), float(lon.max()), float(lat.max()), float(height.min()), float(height.max())],
        'relief_m': float(np.abs(np.diff(height, 2, axis=0)).max() + np.abs(np.diff(height, 2, axis=1)).max()),
        'bytes': Path(path).stat().st_size}


def bake_tile_safely(job):
    try: return bake_tile(job)
    except Exception as error:  # one unavailable image must not stop the other tiles
        return {'level': job[1], 'x': job[2], 'y': job[3], 'failed': f'{type(error).__name__}: {error}'}


def bake_tile(job):
    output, level, ix, iy = job; output = Path(output); record = output / 'tiles' / f'{level}-{ix}-{iy}.json'
    if record.exists(): return json.loads(record.read_text())
    frame = region_frame(DEM); sources = load_sources(DEM, HYDRO, output / 'work'); start = time.time()
    sources['base_elevation_m'] = BASE_M
    sources['pivots'] = region_pivots(DEM, output / 'work')
    maps, stats = author_tile(sources, frame, output / 'work', level, ix, iy)
    (output / 'tiles').mkdir(parents=True, exist_ok=True)
    info = write_glb(output / 'tiles' / f'{level}-{ix}-{iy}.glb', maps, frame, level, ix, iy)
    preview = np.uint8(np.clip(to_srgb(maps['base_color'] * (1 - maps['channel'][..., None]) + np.array(WATER_LINEAR) * maps['channel'][..., None]), 0, 1) * 255)
    (output / 'work/preview').mkdir(parents=True, exist_ok=True); Image.fromarray(preview).resize((512, 512), Image.LANCZOS).save(output / 'work/preview' / f'{level}-{ix}-{iy}.jpg', quality=85)
    if level > 0:  # imagery is large; the root's copy is kept for the state-line tone match
        for image in (output / 'work/imagery').glob(f'{level}-{ix}-{iy}-*'): image.unlink()
    # The mesh heights are kept so a ground-height map for walking cameras can be assembled from the finest tiles.
    (output / 'work/mesh').mkdir(parents=True, exist_ok=True); np.save(output / 'work/mesh' / f'{level}-{ix}-{iy}.npy', maps['mesh'].astype('float32'))
    info.update(level=level, x=ix, y=iy, seconds=round(time.time() - start, 1), **stats); record.write_text(json.dumps(info)); return info


def write_tileset(output):
    """tileset.json over every baked tile; a tile refines only when all four children exist."""
    output = Path(output); tiles = {(t['level'], t['x'], t['y']): t for t in (json.loads(p.read_text()) for p in (output / 'tiles').glob('*.json'))}
    side0 = region_frame(DEM)[3]

    def node(level, ix, iy):
        t = tiles[(level, ix, iy)]; kids = [(level + 1, 2 * ix + i, 2 * iy + j) for j in range(2) for i in range(2)]
        item = {'boundingVolume': {'box': t['box']}, 'geometricError': side0 / 2 ** level / 96, 'refine': 'REPLACE',
                'content': {'uri': f'tiles/{level}-{ix}-{iy}.glb'}, 'extras': {'region_radians_metres': t['region']}}
        if all(k in tiles for k in kids): item['children'] = [node(*k) for k in kids]
        else: item['geometricError'] = 0
        return item

    root = node(0, 0, 0); centre, east, north_axis, up = root_frame(region_frame(DEM))
    # One transform for the whole tree: tileset frame (east, north, up at the region centre) into Earth-centred coordinates.
    root['transform'] = [float(v) for v in [*east, 0, *north_axis, 0, *up, 0, *centre, 1]]
    tileset = {'asset': {'version': '1.1', 'generator': 'san-luis-relief bake.style.relief_tiles'}, 'geometricError': side0 / 48, 'root': root,
        'extras': {'crs_of_sources': 'EPSG:32613', 'heights': 'metres above the WGS84 ellipsoid (NAVD88 plus a constant geoid offset)', 'geoid_offset_m': GEOID_M,
            'vertical_exaggeration': GAIN, 'exaggeration_base_m': BASE_M,
            'frame': 'tile content is in metres east/north/up of the region centre; root.transform places it in ECEF (EPSG:4978)', 'tiles': len(tiles), 'levels': sorted({k[0] for k in tiles}),
            'attribution': 'USGS 3DEP, USGS NHD, USDA NAIP, OpenStreetMap contributors (ODbL)',
            'water': 'each material carries extras.waterMap and extras.flowMap: PNG files beside the tile, for custom shaders',
            'textures': 'KTX2 (KHR_texture_basisu): ETC1S colour and roughness, UASTC normals'}}
    (output / 'tileset.json').write_text(json.dumps(tileset, indent=1) + '\n'); return len(tiles)


def write_ground(output, half_km=22, cell_m=10):
    """Ground-height map for walking cameras: the finest baked mesh heights over a square at the region centre.

    `ground.bin` holds little-endian uint16 decimetres above BASE_M (displayed heights), row zero north.
    """
    output = Path(output); frame = region_frame(DEM); _, west, north, size = frame; n = int(2 * half_km * 1000 / cell_m) + 1
    x0, y0 = west + size / 2 - half_km * 1000, north - size / 2 + half_km * 1000; grid = np.zeros((n, n), 'float32')
    records = sorted((json.loads(p.read_text()) for p in (output / 'tiles').glob('*.json')), key=lambda t: t['level'])
    for t in records:  # finer levels overwrite coarser ones
        tw, tn, side = tile_square(frame, t['level'], t['x'], t['y']); path = output / 'work/mesh' / f"{t['level']}-{t['x']}-{t['y']}.npy"
        c0, c1 = int(np.ceil((tw - x0) / cell_m)), int(np.floor((tw + side - x0) / cell_m)); r0, r1 = int(np.ceil((y0 - tn) / cell_m)), int(np.floor((y0 - tn + side) / cell_m))
        c0, r0, c1, r1 = max(c0, 0), max(r0, 0), min(c1, n - 1), min(r1, n - 1)
        if c0 > c1 or r0 > r1 or not path.exists(): continue
        mesh = np.load(path); m = mesh.shape[0] - 1; rows, cols = np.mgrid[r0:r1 + 1, c0:c1 + 1]
        grid[r0:r1 + 1, c0:c1 + 1] = map_coordinates(mesh, [(y0 - rows * cell_m - tn) / -side * m, (x0 + cols * cell_m - tw) / side * m], order=1, mode='nearest')
    np.clip((grid - BASE_M) * 10, 0, 65535).astype('<u2').tofile(output / 'ground.bin')
    (output / 'ground.json').write_text(json.dumps({'file': 'ground.bin', 'format': 'uint16 little-endian, decimetres above base_m, row zero north', 'size': n, 'cell_m': cell_m,
        'half_km': half_km, 'base_m': BASE_M, 'centre': 'region centre (tileset frame origin)'}, indent=1) + '\n')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=Path('data/relief-tiles'))
    parser.add_argument('--levels', default='0-2'); parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--refine', help='lon,lat,radius_km: bake only tiles of the given levels near this point (whole sibling sets)')
    parser.add_argument('--rivers', type=int, help='bake only tiles of the given levels along NHD lines with at least this map-scale visibility (whole sibling sets)')
    parser.add_argument('--only', help='comma-separated level/x/y tiles to bake')
    parser.add_argument('--ground', action='store_true', help='only write the ground-height map for walking cameras')
    parser.add_argument('--tileset', action='store_true', help='only rewrite tileset.json from the baked tiles')
    args = parser.parse_args(); frame = region_frame(DEM)
    if args.ground: write_ground(args.output); return
    if not args.tileset:
        first, _, last = args.levels.partition('-'); jobs = []; river_points = None
        if args.rivers:
            lines = [densify(line['xy'], 200) for line in load_sources(DEM, HYDRO, args.output / 'work')['lines'] if line['visibility'] >= args.rivers and line['ftype'] != 336]
            river_points = np.concatenate(lines)
        for level in range(int(first), int(last or first) + 1):
            count = 2 ** level; keep = lambda ix, iy: True
            if args.refine:
                lon, lat, radius = map(float, args.refine.split(',')); px, py = transform('EPSG:4326', frame[0], [lon], [lat]); side = frame[3] / count
                # Whole sibling sets: test the parent square against the circle.
                keep = lambda ix, iy: (abs(frame[1] + (ix // 2 * 2 + 1) * side - px[0]) < side + radius * 1000) and (abs(frame[2] - (iy // 2 * 2 + 1) * side - py[0]) < side + radius * 1000)
            if river_points is not None:
                # Parent squares that a river passes through, each grown by a tenth so banks near an edge are covered.
                parent = frame[3] / count * 2; u = (river_points[:, 0] - frame[1]) / parent; v = (frame[2] - river_points[:, 1]) / parent
                wanted = {(int(a), int(b)) for du in (-.1, 0, .1) for dv in (-.1, 0, .1) for a, b in zip(np.floor(u + du), np.floor(v + dv))}
                keep = lambda ix, iy: (ix // 2, iy // 2) in wanted
            jobs += [(str(args.output), level, ix, iy) for iy in range(count) for ix in range(count) if keep(ix, iy)]
        if args.only: jobs = [(str(args.output), *map(int, tile.split('/'))) for tile in args.only.split(',')]
        load_sources(DEM, HYDRO, args.output / 'work'); region_pivots(DEM, args.output / 'work')
        failed = []
        with ProcessPoolExecutor(args.workers) as pool:
            for info in pool.map(bake_tile_safely, jobs):
                if 'failed' in info: failed.append(info); print(f"{info['level']}/{info['x']}/{info['y']} FAILED {info['failed']}", flush=True); continue
                print(f"{info['level']}/{info['x']}/{info['y']} {info['seconds']}s {info['bytes'] // 1024} KB fields {info['parcels']} pivots {info['pivots']} roads {info['roads']} homes {info['buildings']}", flush=True)
    print(write_tileset(args.output), 'tiles in tileset.json')
    if not args.tileset and failed: print(len(failed), 'tiles failed; run the same command again to retry them'); raise SystemExit(1)


if __name__ == '__main__': main()
