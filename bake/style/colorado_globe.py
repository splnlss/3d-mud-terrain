"""Single-resolution Colorado crown. Map truth is retained before artistic spherical bending.

The mesh grid is uniform in *display* space: every vertex is placed where it is seen, and the source map
is sampled through the exact inverse of the display warp. The magnified state therefore gets the dense
vertices and the compressed buffer the sparse ones, for the same vertex budget.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
import rasterio
from rasterio.warp import transform
from scipy.ndimage import gaussian_filter, map_coordinates, distance_transform_edt
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import LineString, mapping
from shapely.strtree import STRtree
import shapely
from bake.style.relief_study import Fields, smoothstep, style_surface

from bake.style.water_palette import WATER_LINEAR, WATER_ROUGHNESS

CRS = '+proj=aeqd +lat_0=39 +lon_0=-105.55 +datum=WGS84 +units=m +no_defs'
DEM_SERVICE = 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage'
HYDRO_SERVICE = 'https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/4/query'
RIVERS = ['Rio Grande', 'Arkansas River', 'Colorado River', 'South Platte River', 'North Platte River', 'Gunnison River', 'San Juan River', 'Green River', 'Yampa River', 'Dolores River', 'Animas River', 'Republican River', 'Canadian River', 'Rio Chama', 'Uncompahgre River', 'White River', 'Eagle River', 'Blue River', 'Cache la Poudre River']
SPAN = 1.6
# Half-angle of the exposed cap: a shallow slice of a large sphere, so the model reads as a wide planet horizon rather than a ball.
CAP_ANGLE = math.radians(46)
# Broad ranges are lifted strongly from a blurred DEM; a finer band adds individual ranges and peaks.
# Both blurs are in display-grid cells, so summits stay knuckled clay, never needles.
GAIN = 62
FINE_GAIN = 22
BROAD_SIGMA = 14
FINE_SIGMA = 3.0
# Soft ceiling (model m): the tallest crowns round over into knuckles instead of rising as spires.
CROWN_ROUNDING = .2
# Elevation that stays on the sphere: plains and plateaus keep the globe's form, only the ranges rise.
DATUM_M = 1500
# Display warp: Mobius shift of the crown toward the state's west/north, then monotone radial magnification.
WARP_FOCUS = (-.14, .10)
WARP_RADIAL = 2.2
# Mapped channel half widths in display metres (the grid is in display space, so widths are constant on screen).
MAJOR_RIVERS = ['Rio Grande', 'Arkansas River', 'Colorado River', 'South Platte River']
RIVER_HALF_WIDTH_M = {'major': 2600, 'other': 1700}
# River names shown in the viewer: (NHD name, anchor lon, lat). Each anchor snaps to the nearest vertex of that river's mapped course.
# Colorado and Rio Grande sit on their southern reaches (Moab; northern New Mexico) so they read in the south-facing hero view.
RIVER_LABELS = [('Colorado River', -109.55, 38.57), ('Green River', -109.68, 40.09), ('Yampa River', -107.9, 40.5),
                ('San Juan River', -108.2, 36.73), ('Rio Grande', -105.72, 36.72), ('Arkansas River', -104.3, 38.2), ('South Platte River', -104.5, 40.4)]
# High-resolution elevation export covering just the coverage circle (about 300 m per pixel).
DEM_BBOX = (-114.2, 32.3, -96.9, 45.7)
DEM_SIZE = (6000, 4650)
# The mud recipe's bank transitions are fixed in model millimetres; scaling the bank distance keeps them proportionate to these narrow channels.
BANK_SCALE = 10
# Labelled places (lon, lat). Ute Mountain Ute Farm and Ranch Enterprise is placed approximately on its irrigated fields, southwest of Cortez near Towaoc.
PLACES = [('Ute Mountain Farm and Ranch', -108.86, 37.32), ('San Luis', -105.4239, 37.2009), ('Rocky Ford', -103.7202, 38.0525), ('Denver', -104.9903, 39.7392)]
# A warm silty tone of the shared water grey: clearly lighter than the clay so rivers stay legible on a matte model, without reading white.
WATER_TONE = (.81, .72, .58)


def project(lon, lat):
    x, y = transform('EPSG:4326', CRS, np.asarray(lon).ravel().tolist(), np.asarray(lat).ravel().tolist())
    return np.asarray(x).reshape(np.shape(lon)), np.asarray(y).reshape(np.shape(lat))


def coverage_radius():
    x, y = project(np.array([-109.06, -102.04, -109.06, -102.04]), np.array([37, 37, 41, 41]))
    return float(np.hypot(x, y).max() + 321868.8 + 2000)


def display_map(x, y):
    """Focus Colorado across the cap and wrap its plains toward the eastern rim.

    A disk automorphism moves the crown west/north; monotone radial magnification
    enlarges the state while retaining every location in the outer buffer.
    Both stages preserve the circular rim and introduce no geographic cut/seam.
    """
    radius = coverage_radius()
    z = (np.asarray(x) + 1j * np.asarray(y)) / radius
    focus = complex(*WARP_FOCUS)
    w = (z - focus) / (1 - np.conjugate(focus) * z)
    r = np.abs(w)
    focused = np.tanh(WARP_RADIAL * r) / np.tanh(WARP_RADIAL)
    w *= focused / np.maximum(r, 1e-12)
    return w.real * radius, w.imag * radius


def display_inverse(wx, wy):
    """Exact inverse of display_map: source map coordinates for displayed coordinates inside the cap."""
    radius = coverage_radius()
    w = (np.asarray(wx) + 1j * np.asarray(wy)) / radius
    r2 = np.minimum(np.abs(w), 1.0)
    r = np.arctanh(r2 * np.tanh(WARP_RADIAL)) / WARP_RADIAL
    w = w * (r / np.maximum(np.abs(w), 1e-12))
    focus = complex(*WARP_FOCUS)
    z = (w + focus) / (1 + np.conjugate(focus) * w)
    return z.real * radius, z.imag * radius


def rim_taper_display(wx, wy):
    """Relief fades to the ground over the outer fifth of the displayed radius, so the compressed buffer meets the ground cleanly."""
    radius = coverage_radius()
    return 1 - smoothstep(np.hypot(wx, wy), radius * .80, radius)


def rim_taper(x, y):
    return rim_taper_display(*display_map(x, y))


def display_relief_scale(wx, wy):
    """min(1, local linear scale of the display warp) on a display-space grid, from the inverse warp's Jacobian."""
    sx, sy = display_inverse(wx, wy)
    det = (np.gradient(sx, axis=1) * np.gradient(sy, axis=0) - np.gradient(sx, axis=0) * np.gradient(sy, axis=1)) / (np.gradient(wx, axis=1) * np.gradient(wy, axis=0))
    return np.clip(1 / np.sqrt(np.maximum(np.abs(det), 1e-12)), 0, 1)


def relief_scale(x, y):
    """Vertical scale that follows the warp's local horizontal scale (capped at 1), so the compressed buffer keeps natural slopes instead of cliffs."""
    wx, wy = display_map(x, y)
    det = (np.gradient(wx, axis=1) * np.gradient(wy, axis=0) - np.gradient(wx, axis=0) * np.gradient(wy, axis=1)) / (np.gradient(x, axis=1) * np.gradient(y, axis=0))
    return np.clip(np.sqrt(np.abs(det)), 0, 1)


def surface_marks(lon, lat, shown, radius):
    """Model positions (source axes, Z up) of lon/lat points on the displayed surface; `shown` is the displayed height on the display grid."""
    n = shown.shape[0]; px = 2 * radius / (n - 1)
    wx, wy = display_map(*project(np.asarray(lon, float), np.asarray(lat, float)))
    h = map_coordinates(shown, [(radius - wy) / px, (wx + radius) / px], order=1)
    return cap_positions_display(wx, wy, h)


def place_marks(shown, radius, places=PLACES):
    xyz = surface_marks([p[1] for p in places], [p[2] for p in places], shown, radius)
    return [{'name': name, 'lon_lat': [lo, la], 'model_xyz': p.tolist()} for (name, lo, la), p in zip(places, xyz)]


def snap_to_rivers(features, labels):
    """Move each (name, lon, lat) anchor onto the nearest vertex of that river's mapped course."""
    snapped = []
    for name, lon, lat in labels:
        points = np.array([v for f in features if f['attributes']['GNIS_NAME'] == name for path in f['geometry']['paths'] for v in path])
        if not len(points): raise ValueError(f'No mapped course for {name}')
        best = points[np.argmin(np.hypot((points[:, 0] - lon) * math.cos(math.radians(lat)), points[:, 1] - lat))]
        snapped.append((name, float(best[0]), float(best[1])))
    return snapped


def write_places(root):
    """Record place marks and river labels in the manifest from a finished package, without re-baking the model."""
    manifest = json.loads((root / 'manifest.json').read_text())
    shown = np.load(root / 'geography.npz')['shown_height']; features = json.loads((root / 'source/rivers.json').read_text())['features']
    manifest['places'] = place_marks(shown, manifest['map_radius_m'])
    manifest['river_labels'] = place_marks(shown, manifest['map_radius_m'], snap_to_rivers(features, RIVER_LABELS))
    manifest['places_note'] = 'Model positions in source axes (Z up); GLB position is (x, z, -y). River labels sit on a vertex of the mapped NHD course. Ute Mountain Farm and Ranch is approximate (irrigated fields near Towaoc).'
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return {'places': manifest['places'], 'river_labels': manifest['river_labels']}


def channel_distance_m(shapes, n, radius):
    """Signed metres from the channel edge (negative inside) for (LineString, half_width_m) pairs on the n x n map grid.

    Cells near a rasterised centreline take their exact distance to the nearest mapped polyline, so a
    channel two or three cells wide keeps its true width and a smooth, continuous bank.
    """
    px = 2 * radius / (n - 1); grid = from_origin(-radius - px / 2, radius + px / 2, px, px)
    centre = rasterize([(mapping(line), 1) for line, _ in shapes], out_shape=(n, n), transform=grid, all_touched=True).astype(bool)
    half = rasterize([(mapping(line), w) for line, w in shapes], out_shape=(n, n), transform=grid, all_touched=True, dtype='float32')
    dist, (ir, ic) = distance_transform_edt(~centre, return_indices=True)
    bank = dist * px - half[ir, ic]
    near = dist * px <= half[ir, ic] + 2 * px
    rows, cols = np.nonzero(near); points = shapely.points(-radius + cols * px, radius - rows * px)
    tree = STRtree([line for line, _ in shapes]); widths = np.array([w for _, w in shapes], 'float32')
    nearest = tree.nearest(points)
    bank[rows, cols] = shapely.distance(points, tree.geometries[nearest]) - widths[nearest]
    return bank.astype('float32')


def channel_level(height, bank_m, px):
    """Height of the nearest channel cell, lightly smoothed: the level each channel bed is cut below."""
    inside = bank_m < 0
    if not inside.any(): return height
    _, (ir, ic) = distance_transform_edt(~inside, return_indices=True)
    return gaussian_filter(height[ir, ic], 2)


def cap_positions(x, y, height):
    """Source map coordinates through the display warp onto the cap."""
    return cap_positions_display(*display_map(x, y), height)


def cap_positions_display(x, y, height):
    """Map displayed radial distance to a sphere whose cap of half-angle CAP_ANGLE stands above z=0."""
    radius = coverage_radius(); alpha = CAP_ANGLE; sphere = (SPAN / 2) / math.sin(alpha)
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = np.hypot(x, y); theta = np.minimum(d / radius, 1) * alpha
    r = sphere + height
    k = r * np.sin(theta) / np.maximum(d, 1e-12)
    return np.stack([x * k, y * k, r * np.cos(theta) - sphere * math.cos(alpha)], axis=-1)


def border_crossings(points, axis, value):
    p = np.asarray(points); a, b = p[:-1], p[1:]
    hit = ((a[:, axis] <= value) & (b[:, axis] > value)) | ((b[:, axis] <= value) & (a[:, axis] > value))
    a, b = a[hit], b[hit]
    return (a + (b - a) * ((value - a[:, axis]) / (b[:, axis] - a[:, axis]))[:, None]).tolist()


def read_json(url):
    with urlopen(url, timeout=240) as response:
        result = json.load(response)
    if 'error' in result: raise RuntimeError(result['error'])
    return result


def fetch_sources(root):
    source = root / 'source'; source.mkdir(parents=True, exist_ok=True)
    dem = source / 'dem-hires.tif'; rivers = source / 'rivers.json'
    if not dem.exists():
        params = dict(bbox=','.join(map(str, DEM_BBOX)), bboxSR=4326, imageSR=4326, size='%d,%d' % DEM_SIZE, format='tiff', compression='LZ77', pixelType='F32', noData=-999999, interpolation='RSP_BilinearInterpolation', renderingRule=json.dumps({'rasterFunction':'None'}), f='json')
        url = DEM_SERVICE + '?' + urlencode(params)
        info = read_json(url); payload = urlopen(info['href'], timeout=900).read()
        temp = dem.with_suffix('.part'); temp.write_bytes(payload)
        with rasterio.open(temp) as src:
            if src.count != 1 or src.dtypes[0] != 'float32' or (src.width, src.height) != DEM_SIZE: raise ValueError('Expected raw float32 elevation at the requested size')
        temp.replace(dem); (source / 'dem-hires-request.json').write_text(json.dumps({'url':url, 'response':info}, indent=2))
    if not rivers.exists():
        features = []; offset = 0
        where = 'GNIS_NAME IN (' + ','.join("'" + name + "'" for name in RIVERS) + ')'
        while True:
            params = dict(where=where, geometry='-115,31,-96,47', geometryType='esriGeometryEnvelope', inSR=4326, spatialRel='esriSpatialRelIntersects', outSR=4326, outFields='GNIS_NAME,COMID', returnGeometry='true', f='json', resultOffset=offset, resultRecordCount=2000, orderByFields='OBJECTID')
            data = read_json(HYDRO_SERVICE + '?' + urlencode(params)); features += data['features']
            if not data.get('exceededTransferLimit'): break
            offset += len(data['features'])
        if not features: raise ValueError('USGS returned no rivers')
        rivers.write_text(json.dumps({'features':features}))
    return dem, json.loads(rivers.read_text())['features']


def geographic_checks(features):
    checks = {}
    for name, axis, value, expected in [('Rio Grande', 1, 37., (-105.8, -105.6)), ('Arkansas River', 0, -102.05, (37.9, 38.2))]:
        points = []
        for f in features:
            if f['attributes']['GNIS_NAME'] != name: continue
            for p in f['geometry']['paths']:
                points += border_crossings(p, axis, value)
        # Retain only crossings near Colorado; the same named river can cross the meridian elsewhere.
        points = [p for p in points if expected[0] < p[1-axis] < expected[1]]
        if not points: raise ValueError(f'Mapped {name} is missing its Colorado border crossing')
        checks[name] = points
    return checks


def sculpt_elevation(true, scale):
    """Lift broad connected ranges strongly, without turning fine summits into needles."""
    broad = gaussian_filter(true, BROAD_SIGMA)
    rounded = gaussian_filter(true, FINE_SIGMA)
    lifted = np.maximum(broad - DATUM_M, 0) * scale * GAIN + (rounded - broad) * scale * FINE_GAIN
    if scale >= .01: return lifted   # unit-scale callers (tests) measure the raw shaping
    return CROWN_ROUNDING * np.tanh(lifted / CROWN_ROUNDING)


def author(root, n):
    dem_path, features = fetch_sources(root); checks = geographic_checks(features)
    radius = coverage_radius(); px = 2 * radius / (n - 1); scale = SPAN / (2 * radius)
    # Display-space grid; each vertex samples the source map through the inverse warp.
    dx, dy = np.meshgrid(np.linspace(-radius, radius, n), np.linspace(radius, -radius, n))
    sx, sy = display_inverse(dx, dy)
    lon, lat = transform(CRS, 'EPSG:4326', sx.ravel(), sy.ravel())
    with rasterio.open(dem_path) as src:
        data = gaussian_filter(src.read(1), .7); lon, lat = np.array(lon), np.array(lat)
        cols = (lon - src.transform.c) / src.transform.a - .5; rows = (lat - src.transform.f) / src.transform.e - .5
        true = map_coordinates(data, [rows, cols], order=1, mode='nearest').reshape(n, n)
    if not np.isfinite(true).all() or true.min() < -1000: raise ValueError('DEM contains missing elevations')
    true = gaussian_filter(true, 1.0)
    shapes = []; river_features = []
    for f in features:
        name = f['attributes']['GNIS_NAME']; half_width = RIVER_HALF_WIDTH_M['major' if name in MAJOR_RIVERS else 'other']
        for path in f['geometry']['paths']:
            xy = np.column_stack(project(*np.array(path).T))
            if np.hypot(xy[:, 0], xy[:, 1]).min() > radius: continue
            # Densify in source metres before warping, so each course bends smoothly with the map.
            dense = np.array(shapely.segmentize(LineString(xy), 1500).coords)
            shapes.append((LineString(np.column_stack(display_map(dense[:, 0], dense[:, 1]))), half_width))
            river_features.append({'type':'Feature', 'properties':{'name':name}, 'geometry':{'type':'LineString','coordinates':path}})
    bank_m = channel_distance_m(shapes, n, radius); bank = bank_m * scale
    f = Fields(n, SPAN, 404)
    height = sculpt_elevation(true, scale)
    # Rounded DEM summits carry the silhouette; clustered mud detail uses the existing shared recipe.
    height += (.004 * f.noise(.035) + .002 * f.noise(.016)) * smoothstep(true, 1400, 2600)
    datum = gaussian_filter(height, 5)
    land = height - datum
    maps = style_surface(f, land, bank * BANK_SCALE, bank * BANK_SCALE, datum=datum, true_terrain=True)
    # The recipe cuts each bed below the broad datum; re-seat it below the valley the mapped river actually follows.
    maps['height'] += (channel_level(height, bank_m, px) - datum) * maps['channel']
    maps['height'] = gaussian_filter(maps['height'], .65)
    snow = smoothstep(true + 140 * f.noise(.035), 3100, 3920) * smoothstep(f.noise(.055), -.8, .6) * (1-maps['channel'])
    maps['base_color'] = maps['base_color'] * (1-snow[...,None]) + np.array([.82,.84,.81]) * snow[...,None]
    maps['roughness'] = maps['roughness'] * (1-snow) + .84 * snow
    # Paint water with a sharper mask than the recipe's silt blend, so bank vertices do not keep a pale wet fringe.
    wet = gaussian_filter(smoothstep(maps['channel'], 0, .7), .7)
    maps['base_color'] = maps['base_color'] * (1-wet[...,None]) + np.array(WATER_LINEAR) * np.array(WATER_TONE) * wet[...,None]
    maps['roughness'] = maps['roughness'] * (1-wet) + WATER_ROUGHNESS * wet
    shown = (maps['height'] * rim_taper_display(dx, dy) * display_relief_scale(dx, dy)).astype('float32')
    positions = cap_positions_display(dx, dy, shown)
    ids = np.arange(n*n).reshape(n,n)
    faces = np.stack([ids[:-1,:-1], ids[1:,:-1], ids[1:,1:], ids[:-1,1:]], axis=-1)
    valid = np.hypot(dx, dy) <= radius; faces = faces[valid[:-1,:-1] & valid[1:,:-1] & valid[1:,1:] & valid[:-1,1:]]
    used, inv = np.unique(faces, return_inverse=True)
    np.savez(root / 'model.npz', positions=positions.reshape(-1,3)[used].astype('float32'), faces=inv.reshape(-1,4).astype('int32'), color=maps['base_color'].reshape(-1,3)[used].astype('float32'), roughness=maps['roughness'].ravel()[used], xy=np.stack([sx,sy],-1).reshape(-1,2)[used], display_xy=np.stack([dx,dy],-1).reshape(-1,2)[used], source_height=true.ravel()[used])
    np.savez(root / 'geography.npz', grid='display', height=true, styled_height=maps['height'], shown_height=shown, snow=snow, bank_m=bank_m, channel=maps['channel'])
    (root / 'rivers.geojson').write_text(json.dumps({'type':'FeatureCollection','features':river_features}))
    # Border is a separate toggleable geographic guide, draped on exactly the same surface.
    border = []
    for a,b in [((-109.05,37),(-102.05,37)),((-102.05,37),(-102.05,41)),((-102.05,41),(-109.05,41)),((-109.05,41),(-109.05,37))]:
        coords = np.linspace(a,b,400); border.extend((surface_marks(coords[:,0], coords[:,1], shown, radius) + [0, 0, .0015]).tolist())
    (root / 'border.json').write_text(json.dumps(border))
    crossings_xyz = {name: surface_marks(np.array(pts)[:,0], np.array(pts)[:,1], shown, radius).tolist() for name, pts in checks.items()}
    manifest = {'name':'Colorado crown', 'lods':1, 'resolution':n, 'mesh_grid':'uniform in display space; source map sampled through the exact inverse warp', 'axes':'source Z up, +X east, +Y north; GLB Y up, north -Z', 'units':'model metres', 'map_crs':CRS, 'map_radius_m':radius, 'buffer_miles':200, 'coverage':'Circular extent enclosing Colorado corners plus 321868.8 metres in the local equidistant projection; extra 2 km margin', 'cap_half_angle_degrees':math.degrees(CAP_ANGLE), 'sphere_exposed_diameter_fraction':(1-math.cos(CAP_ANGLE))/2, 'display_warp':{'focus_normalized':list(WARP_FOCUS),'radial_focus':WARP_RADIAL,'rim_taper':'relief fades over display radius .80R..R','note':'State enlarged across crown, eastern plains wrapped onto the right shoulder; terrain, channels, snow and geographic guides share the warp'}, 'water_linear':WATER_LINEAR, 'water_tone':WATER_TONE, 'water_roughness':WATER_ROUGHNESS, 'span_m':SPAN, 'vertical_gain':{'broad_landforms':GAIN,'fine_relief':FINE_GAIN,'broad_smoothing_grid_pixels':BROAD_SIGMA,'fine_smoothing_grid_pixels':FINE_SIGMA,'crown_rounding_m':CROWN_ROUNDING}, 'height_datum_m':DATUM_M, 'dem':{'bbox_lon_lat':DEM_BBOX,'size_px':DEM_SIZE}, 'river_full_width_display_m':{k:2*v for k,v in RIVER_HALF_WIDTH_M.items()}, 'major_rivers':MAJOR_RIVERS, 'bank_scale':BANK_SCALE, 'channel_bed':'recipe bed cut below the sculpted height of the nearest channel cell', 'sources':{'elevation':DEM_SERVICE,'hydrography':HYDRO_SERVICE,'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [dem_path,root/'source/rivers.json']}}, 'border_crossings_lon_lat':checks, 'border_crossings_model_xyz':crossings_xyz, 'rim_taper_display_fraction':[.80,1.0], 'relief_scale':'heights multiplied by min(1, local linear scale of the display warp)', 'style':'Shared relief_study.style_surface recipe, softened DEM, true-height patchy snow, continuous narrow mapped channels in the shared San Luis water palette; widths and spherical curvature are artistic exaggerations', 'vertices':len(used),'quads':len(faces)}
    (root / 'manifest.json').write_text(json.dumps(manifest,indent=2))
    write_places(root)
    review_map(root, features, dem_path, radius, checks)
    print(json.dumps({'vertices':len(used),'crossings':checks}),flush=True)


def review_map(root, features, dem_path, radius, checks, size=1400):
    """North-up diagnostic map in unwarped source coordinates: elevation, mapped rivers, state border and verified crossings."""
    from PIL import Image, ImageDraw
    g = np.linspace(-radius, radius, 700); x, y = np.meshgrid(g, g[::-1])
    lon, lat = transform(CRS, 'EPSG:4326', x.ravel(), y.ravel())
    with rasterio.open(dem_path) as src:
        data = src.read(1); lon, lat = np.array(lon), np.array(lat)
        dem = map_coordinates(data, [(lat - src.transform.f) / src.transform.e - .5, (lon - src.transform.c) / src.transform.a - .5], order=1, mode='nearest').reshape(700, 700)
    tone = smoothstep(dem,500,4300)
    color = np.stack([.85-.45*tone,.78-.40*tone,.62-.30*tone],-1)
    image = Image.fromarray(np.uint8(color*255)).resize((size,size)); draw = ImageDraw.Draw(image)
    def pixels(coords):
        xy = np.column_stack(project(*np.array(coords).T)); return [tuple(p) for p in np.column_stack([(xy[:,0]+radius)/(2*radius)*size,(radius-xy[:,1])/(2*radius)*size])]
    for f in features:
        for path in f['geometry']['paths']: draw.line(pixels(path), fill=(97,158,184), width=3 if f['attributes']['GNIS_NAME'] in MAJOR_RIVERS else 2)
    for a,b in [((-109.05,37),(-102.05,37)),((-102.05,37),(-102.05,41)),((-102.05,41),(-109.05,41)),((-109.05,41),(-109.05,37))]: draw.line(pixels(np.linspace(a,b,200)),fill='white',width=3)
    for name, points in checks.items():
        for px_,py_ in pixels(points):
            draw.ellipse((px_-7,py_-7,px_+7,py_+7),fill='red'); draw.text((px_+12,py_),name,fill='black',stroke_width=1,stroke_fill='white')
    draw.text((24,24),'SOURCE MAP / NORTH UP / white = Colorado / red = verified border crossings',fill='black')
    image.save(root/'geography-review.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--resolution',type=int,default=1537); parser.add_argument('--places-only',action='store_true',help='update manifest place marks from an existing package')
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    if args.places_only: print(json.dumps(write_places(args.output),indent=2))
    else: author(args.output,args.resolution)
