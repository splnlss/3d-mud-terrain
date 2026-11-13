"""Relief style on the real Culebra Creek patch: DEM landforms, mapped creek, DEM drainage.

Model metres: the 2 km patch becomes a 1.6 m relief (1:1250 horizontally). Channels
are never invented: the wide channel is the mapped NHD creek, the narrow ones are
drainage lines computed from the DEM itself, and the pools are mapped NHD ponds.
`data/relief-patch/reference/naip-overlay.jpg` checks them against aerial imagery. Land height is the DEM's height above
its nearest channel, so every mass and valley sits where the source terrain has one.
"""
import argparse
import heapq
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, grey_opening, map_coordinates, uniform_filter
from scipy.spatial import cKDTree
from rasterio.warp import transform_geom
from shapely import contains_xy
from shapely.geometry import box, shape
from PIL import Image
from bake.style.fields import field_parcels, woody_cover
from bake.style.relief_study import Fields, mound_field, smoothstep, style_surface, write_maps

NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def drainage(dem):
    """Priority-flood D8: downstream cell index and contributing cell count for each DEM cell."""
    n, m = dem.shape; done = np.zeros((n, m), bool); down = np.full(n * m, -1); order = []
    heap = []
    for r in range(n):
        for c in range(m):
            if r in (0, n - 1) or c in (0, m - 1):
                heapq.heappush(heap, (float(dem[r, c]), r, c)); done[r, c] = True
    while heap:
        level, r, c = heapq.heappop(heap); order.append(r * m + c)
        for dr, dc in NEIGHBOURS:
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < m and not done[rr, cc]:
                done[rr, cc] = True; down[rr * m + cc] = r * m + c
                heapq.heappush(heap, (max(float(dem[rr, cc]), level), rr, cc))
    area = np.ones(n * m)
    for cell in reversed(order):
        if down[cell] >= 0: area[down[cell]] += area[cell]
    return down, area.reshape(n, m)


def drainage_paths(dem, spacing, min_cells, min_length_m):
    """Smoothed drainage polylines as arrays of (col, row, contributing cells), longest first."""
    down, area = drainage(dem); cols = dem.shape[1]; flat = area.ravel()
    chosen = flat >= min_cells; fed = np.zeros(len(flat), bool)
    fed[down[chosen & (down >= 0)]] = True
    heads = sorted(np.flatnonzero(chosen & ~fed), key=lambda cell: -flat[cell]); seen = set(); paths = []
    # Trace every head to the patch edge or a line already traced, largest catchments first.
    for head in sorted(heads, key=lambda cell: flat[cell]):
        cell, chain = head, []
        while cell >= 0:
            chain.append(cell)
            if cell in seen: break
            seen.add(cell); cell = down[cell]
        if len(chain) * spacing < min_length_m: continue
        rc = np.array([divmod(c, cols) for c in chain], float)
        # D8 only steps to eight neighbours; smoothing along the line removes its staircases and 45-degree runs.
        sigma = 30 / spacing
        smooth = np.column_stack([gaussian_filter(rc[:, 1], sigma, mode='nearest'), gaussian_filter(rc[:, 0], sigma, mode='nearest')])
        smooth[-1] = rc[-1, ::-1]
        paths.append(np.column_stack([smooth, gaussian_filter(flat[chain], sigma, mode='nearest')]))
    return paths


def follow_vegetation(x, z, woody, size, reach_m=55):
    """Shift a drainage line sideways onto the strip of trees and brush that marks the real watercourse.

    A 10 m DEM places small creeks tens of metres off. Where imagery shows woody cover within reach,
    the line moves to it; elsewhere it keeps the DEM course. Offsets are smoothed along the line.
    """
    scale = woody.shape[0] / size; half = size / 2; score = gaussian_filter(woody, 5 * scale)
    tx, tz = np.gradient(x), np.gradient(z); norm = np.hypot(tx, tz) + 1e-9; nx, nz = -tz / norm, tx / norm
    offsets = np.linspace(-reach_m, reach_m, 45)
    px = x[:, None] + nx[:, None] * offsets; pz = z[:, None] + nz[:, None] * offsets
    value = map_coordinates(score, [(pz + half) * scale, (px + half) * scale], order=1, mode='nearest') - .25 * (offsets / reach_m) ** 2
    best = offsets[value.argmax(1)]; found = value.max(1) > .2
    step = np.hypot(np.diff(x), np.diff(z)).mean()
    shift = gaussian_filter(np.where(found, best, 0.), 18 / step, mode='nearest')
    return x + nx * shift, z + nz * shift, gaussian_filter(found.astype(float), 25 / step, mode='nearest')


def densify(line, step):
    """Points every `step` along a polyline whose first two columns are coordinates."""
    lengths = np.r_[0, np.cumsum(np.hypot(*np.diff(line[:, :2], axis=0).T))]
    at = np.arange(0, lengths[-1], step)
    return np.column_stack([np.interp(at, lengths, column) for column in line.T])


def patch_terrain(package, reference, woody=None):
    """Ground heights for the patch (m, row zero north) and a note naming their source.

    With a Google 3D Tiles surface present, the USGS bare-earth DEM stays the base and Google adds
    the finer shape. Google's mesh includes trees: single trees and narrow belts are removed by a
    25 m opening, and under broad forest canopy the DEM is used alone.
    """
    dem = np.load(Path(package) / 'source/dem.npy'); fine = Path(reference) / 'google-surface.npy'
    if not fine.exists(): return dem, 'USGS 10 m DEM'
    surface = np.load(fine); n = surface.shape[0]; spacing = json.loads((Path(package) / 'manifest.json').read_text())['size_m'] / (n - 1)
    rows, cols = np.mgrid[0:n, 0:n] * ((dem.shape[0] - 1) / (n - 1)); base = map_coordinates(dem, [rows, cols], order=3, mode='nearest')
    surface = surface - np.median(surface - base)  # ellipsoid heights to the DEM's datum
    detail = np.clip(grey_opening(surface, size=int(25 / spacing) | 1) - base, -8, 4)
    if woody is not None:
        cover = map_coordinates(woody, [rows * 0 + np.mgrid[0:n, 0:n][0] * ((woody.shape[0] - 1) / (n - 1)), np.mgrid[0:n, 0:n][1] * ((woody.shape[1] - 1) / (n - 1))], order=1)
        detail = detail * (1 - smoothstep(gaussian_filter(cover, 40 / spacing), .35, .6))
    return (base + gaussian_filter(detail, 3 / spacing)).astype('float32'), 'USGS 10 m DEM with Google 3D Tiles detail (2.5 m)'


def channel_samples(package, min_cells, creek_half_m, gully_half_m, min_length_m=300, min_incision_m=1.0, join_within_m=450, bridge_m=250, woody=None, terrain=None):
    """Dense points along every channel: x-east, z-south (m), half-width (m), surface level (m), and the smoothed DEM."""
    package = Path(package); m = json.loads((package / 'manifest.json').read_text())
    dem = np.load(package / 'source/dem.npy') if terrain is None else terrain
    size = m['size_m']; half = size / 2; spacing = size / (dem.shape[0] - 1)
    # Source grids carry tile seams, terrace edges and mesh facets; they must not be exaggerated into ruled lines.
    smooth = gaussian_filter(dem, 12 / spacing); valley = gaussian_filter(dem, 15 / spacing); incision = gaussian_filter(dem, 50 / spacing) - smooth
    min_cells = min_cells * (10 / spacing) ** 2  # the threshold is stated in 10 m cells
    level = lambda x, z: map_coordinates(valley, [(z + half) / spacing, (x + half) / spacing], order=1, mode='nearest')
    points = []
    for feature in json.loads((package / 'source/water.geojson').read_text())['features']:
        xz = densify(np.array(feature['geometry']['coordinates'], float)[:, :2], 1.5)
        points.append(np.column_stack([xz, np.full(len(xz), creek_half_m), level(xz[:, 0], xz[:, 1])]))
    creek = cKDTree(np.concatenate(points)[:, :2])
    for path in drainage_paths(valley, spacing, min_cells, min_length_m):
        line = densify(path, 1.5 / spacing); x = line[:, 0] * spacing - half; z = line[:, 1] * spacing - half
        wooded = np.zeros(len(x))
        if woody is not None: x, z, wooded = follow_vegetation(x, z, woody, size)
        # A tributary runs until it meets the river's own centreline, so the two always join.
        reach = creek.query(np.column_stack([x, z]))[0]; touches = reach < creek_half_m
        end = len(x) if not touches.any() else int(np.argmax(touches)) + 1
        if end * 1.5 < min_length_m: continue  # a DEM thalweg that merely shadows the mapped river
        # D8 also rules straight lines across smooth fans and fields. Keep a reach only where the ground
        # is cut below its surroundings or the imagery shows a tree line along it.
        cut = gaussian_filter(map_coordinates(incision, [line[:end, 1], line[:end, 0]], order=1), 40) > min_incision_m
        real = cut | (wooded[:end] > .45)
        step_m = 1.5; edges = np.flatnonzero(np.diff(np.r_[False, real, False].astype(int))); runs = []
        for start, stop in zip(edges[::2], edges[1::2]):
            # Short unsupported gaps are bridged; long ones would rule a straight DEM line across open ground.
            if runs and (start - runs[-1][1]) * step_m < bridge_m: runs[-1][1] = stop
            else: runs.append([start, stop])
        if runs and (end - runs[-1][1]) * step_m < join_within_m: runs[-1][1] = end
        for start, stop in runs:
            if (stop - start) * step_m < min_length_m: continue
            # Width grows gently with contributing area; a gully never rivals the river. The head tapers in.
            width = gully_half_m * np.clip(np.sqrt(line[start:stop, 2] / min_cells), 1, 2.0) * np.clip(np.arange(stop - start) / 80, .35, 1)
            points.append(np.column_stack([x[start:stop], z[start:stop], width, level(x[start:stop], z[start:stop])]))
    hydro = json.loads((package / 'source/config.json').read_text())['hydrography']; cx, cy = m['origin_utm_m']
    for feature in json.loads(Path(hydro).read_text())['layers']['12']:
        pond = shape(transform_geom('EPSG:4326', m['source_crs'], feature['geometry'])).intersection(box(cx - half, cy - half, cx + half, cy + half))
        if pond.is_empty or pond.area < 400: continue
        # Mapped ponds become level silt: a fill of small discs approximates the polygon.
        x0, y0, x1, y1 = pond.bounds; gx, gy = np.meshgrid(np.arange(x0, x1, 3), np.arange(y0, y1, 3))
        inside = contains_xy(pond, gx.ravel(), gy.ravel()); x = gx.ravel()[inside] - cx; z = cy - gy.ravel()[inside]
        points.append(np.column_stack([x, z, np.full(len(x), 3.0), np.full(len(x), np.median(level(x, z)))]))
    return np.concatenate(points), smooth, size


def tilled_ground(f, imagery, size, row_spacing_m=7.5, pixel_m=None):
    """Farmland grids for `style_surface` from colour-infrared imagery (path or array) of the patch square."""
    image = imagery if isinstance(imagery, np.ndarray) else Image.open(imagery).convert('RGB')
    ids, parcels = field_parcels(image, size, pixel_m=pixel_m)
    ratio = (ids.shape[0] - 1) / (f.n - 1); rows, cols = np.mgrid[0:f.n, 0:f.n] * ratio
    # Wobble the lookup slightly so parcel outlines read as pressed by hand, not ruled.
    wobble = min(4 / size * ids.shape[0], 1.5)
    rr = np.clip(np.rint(rows + wobble * f.noise(.06)), 0, ids.shape[0] - 1).astype(int); cc = np.clip(np.rint(cols + wobble * f.noise(.06)), 0, ids.shape[1] - 1).astype(int)
    grid = ids[rr, cc]; metres = size / (ids.shape[0] - 1)
    wave = np.zeros((f.n, f.n), 'float32'); tone = np.zeros((f.n, f.n), 'float32')
    for number, parcel in enumerate(parcels, 1):
        here = grid == number; cx, cy = parcel['centre_px']; dx = (cols[here] - cx) * metres; dy = (rows[here] - cy) * metres
        across = np.hypot(dx, dy) if parcel['pivot'] else dx * np.cos(parcel['row_normal_rad']) + dy * np.sin(parcel['row_normal_rad'])
        wave[here] = np.sin(2 * np.pi * across / row_spacing_m); tone[here] = parcel['tone']
    solid = (grid > 0).astype('float32'); mask = gaussian_filter(solid, .0025 / f.px)
    edge = np.clip(gaussian_filter(np.abs(solid - gaussian_filter(solid, .002 / f.px)), .0012 / f.px) * 3.5, 0, 1) * (mask > .05)
    for number in range(1, len(parcels)):  # grooves between touching parcels
        own = (grid == number).astype('float32'); edge = np.maximum(edge, np.clip(4 * gaussian_filter(own, .002 / f.px) * (solid - own), 0, 1))
    return {'mask': np.clip(mask * 1.3 - .15, 0, 1).astype('float32'), 'rows': wave, 'edge': edge.astype('float32'), 'tone': gaussian_filter(tone, .002 / f.px)}, parcels


def ground_shade(f, photo, cir, size, blur_m=3):
    """How dark the real ground looks from above, 0 light .. 1 dark, from imagery of the patch square.

    Dark means visibly dark ground or woody cover, which separates creek-side brush from smooth bright fields.
    """
    lum = np.asarray(Image.open(photo).convert('L'), float); scale = lum.shape[0] / size
    lo, hi = np.percentile(gaussian_filter(lum, 3), [3, 90]); dark = 1 - np.clip((lum - lo) / (hi - lo), 0, 1)
    shade = gaussian_filter(np.maximum(dark ** 1.3, .95 * woody_cover(Image.open(cir).convert('RGB'))), blur_m * scale)
    ratio = (lum.shape[0] - 1) / (f.n - 1); rows, cols = np.mgrid[0:f.n, 0:f.n] * ratio
    # A slight nudge so cover edges are not traced pixel for pixel.
    nudge = 1.5 * scale
    return map_coordinates(shade, [rows + nudge * f.noise(.02), cols + nudge * f.noise(.02)], order=1, mode='nearest').astype('float32')


def road_tracks(f, roads, size, x, z, scale):
    """Pressed-track strength 0..1 for mapped roads; public roads are drawn wider than farm tracks."""
    points = []
    for feature in json.loads(Path(roads).read_text())['features']:
        line = densify(np.array(feature['geometry']['coordinates'], float), 1.5)
        half = 3.5 if feature['properties']['highway'] in ('track', 'service', 'path') else 4.5
        points.append(np.column_stack([line, np.full(len(line), half)]))
    points = np.concatenate(points); points = points[(np.abs(points[:, :2]) < size / 2 + 20).all(1)]
    dist, ids = cKDTree(points[:, :2]).query(np.column_stack([x.ravel(), z.ravel()]), workers=-1)
    reach = ((dist - points[ids, 2]) * scale).reshape(x.shape) + .0006 * f.noise(.03)
    return (1 - smoothstep(reach, -.0005, .0012)).astype('float32')


def author_patch(package, resolution=3200, span=1.6, seed=404, gain=2.0, detail_gain=1.2, min_cells=500, creek_half_m=6, gully_half_m=2.5, reference='data/relief-patch/reference'):
    reference = Path(reference); roads, imagery, photo = reference / 'roads.geojson', reference / 'naip-cir.png', reference / 'naip.jpg'
    f = Fields(resolution, span, seed)
    woody = woody_cover(Image.open(imagery).convert('RGB')) if Path(imagery).exists() else None
    terrain, terrain_source = patch_terrain(package, reference, woody)
    samples, dem, size = channel_samples(package, min_cells, creek_half_m, gully_half_m, woody=woody, terrain=terrain)
    scale = span / size; half = size / 2
    axis = np.linspace(-half, half, resolution); x, z = np.meshgrid(axis, axis)
    dist, ids = cKDTree(samples[:, :2]).query(np.column_stack([x.ravel(), z.ravel()]), workers=-1)
    flow = ((dist - samples[ids, 2]) * scale).reshape(x.shape).astype('float32')
    flow = gaussian_filter(flow, .0012 / f.px)  # rounds the 10 m DEM-cell staircase of drainage lines
    bank = flow + .0009 * f.noise(.03) + .0004 * f.noise(.012)
    # Each channel keeps its own source elevation; land is measured above the nearest one.
    surface = gaussian_filter(samples[ids, 3].reshape(x.shape), .03 / f.px)
    ratio = (dem.shape[0] - 1) / (resolution - 1); rows, cols = np.mgrid[0:resolution, 0:resolution] * ratio
    ground = map_coordinates(dem, [rows, cols], order=3, mode='nearest')
    above = np.clip(ground - surface, 0, None) * scale * gain
    # Pressed knobs break the DEM's broad slopes into separate tops without moving its ridges or valleys.
    knobs = .62 + .5 * smoothstep(f.noise(.085), -1.0, 1.0) * smoothstep(above, .004, .03)
    # Source micro-relief (features under ~120 m) is exaggerated so real spurs and swales lead the sculpt.
    detail = (ground - gaussian_filter(ground, 120 / size * (resolution - 1))) * scale * gain * detail_gain
    # Faint authored swells keep level ground from reading as a machined plane.
    filler = .18 * mound_field(f) * (1 - .65 * smoothstep(above, .03, .09))  # low swells only: big invented hills contradict the imagery
    # Farmland keeps the DEM's own gentle grade: no knobs, exaggeration or added masses.
    tilled, parcels = tilled_ground(f, imagery, size) if Path(imagery).exists() else (None, [])
    wild = 1 if tilled is None else 1 - tilled['mask'] * smoothstep(bank, .006, .02)
    if tilled is not None: tilled['mask'] = (1 - wild).astype('float32'); tilled['edge'] *= tilled['mask'] > .02
    shade = ground_shade(f, photo, imagery, size) if Path(photo).exists() and Path(imagery).exists() else None
    tracks = road_tracks(f, roads, size, x, z, scale) * smoothstep(bank, .0, .0015) if Path(roads).exists() else None
    if tracks is not None: wild = wild * (1 - .7 * tracks)
    # Beside a channel the DEM's terraces and cut banks are already sharp; exaggerating them builds cliffs.
    wild = wild * smoothstep(flow, .012, .075)
    land = np.clip(above * (1 + (knobs - 1) * wild) + (detail + filler) * wild, 0, None) + .004
    maps = style_surface(f, land.astype('float32'), bank, flow, ((surface - surface.min()) * scale * gain).astype('float32'), tilled, shade, tracks)
    # Downstream direction: along the channel, turned to point down the source water level.
    gz, gx = np.gradient(gaussian_filter(flow, .002 / f.px)); dz, dx = np.gradient(gaussian_filter(surface, .02 / f.px))
    tx, tz = -gz, gx; sign = np.where(tx * -dx + tz * -dz >= 0, 1, -1); norm = np.hypot(tx, tz) + 1e-9
    maps['flow_dir'] = np.dstack([sign * tx / norm, sign * tz / norm]).astype('float32')
    return maps, {'kind': 'relief style on real patch', 'patch': json.loads((Path(package) / 'source/config.json').read_text()).get('selection', {}).get('name'), 'span_m': span, 'seed': seed,
        'source_size_m': size, 'terrain': terrain_source, 'horizontal_scale': scale, 'height_gain': gain,
        'channels': {'creek': 'NHD Culebra Creek centreline', 'gullies': f'DEM D8 drainage, contributing area >= {min_cells} cells, shifted onto the tree line seen in imagery and run to the river',
            'ponds': 'NHD waterbody polygons', 'tone': 'dark crust and light/dark clay follow NAIP darkness and woody cover (3 m blur) with noise',
            'roads': 'OpenStreetMap, USGS National Map and Census TIGER roads as pressed tracks',
            'fields': f'{len(parcels)} parcels from NAIP colour-infrared imagery ({sum(p["pivot"] for p in parcels)} centre pivots)', 'dem_smoothing': 'gaussian, sigma 12 m',
            'creek_half_width_source_m': creek_half_m, 'gully_half_width_source_m': gully_half_m},
        'artistic_departures': ['vertical gain', 'river drawn about 12 m wide and tributaries 5-10 m', 'pressed knobs and lumps on DEM slopes',
            'source micro-relief exaggerated', 'faint authored swells on level wild ground'],
        'note': 'Row zero is north. Colour holds no baked light.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package', type=Path, default=Path('data/style-patch'))
    parser.add_argument('--output', type=Path, required=True); parser.add_argument('--resolution', type=int, default=3200)
    parser.add_argument('--reference', type=Path, help='fetched imagery and roads; default OUTPUT/reference')
    args = parser.parse_args(); write_maps(args.output, *author_patch(args.package, args.resolution, reference=args.reference or args.output / 'reference'))
