"""Single-resolution Colorado crown. Map truth is retained before artistic spherical bending."""
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
# Broad-range gain is read after the warp's ~2x horizontal magnification; the rounded blur keeps summits knuckled, not needled.
GAIN = 62
FINE_GAIN = 16
# Elevation that stays on the sphere: plains and plateaus keep the globe's form, only the ranges rise.
DATUM_M = 1500
# Display warp: Mobius shift of the crown toward the state's west/north, then monotone radial magnification.
WARP_FOCUS = (-.14, .10)
WARP_RADIAL = 2.2
# Mapped channel half widths (m). Judged by apparent width after the warp's ~2x crown magnification.
MAJOR_RIVERS = ['Rio Grande', 'Arkansas River', 'Colorado River', 'South Platte River']
RIVER_HALF_WIDTH_M = {'major': 1800, 'other': 1150}
# The mud recipe's bank transitions are fixed in model millimetres; scaling the bank distance keeps them proportionate to these narrow channels.
BANK_SCALE = 10
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


def rim_taper(x, y):
    """Relief fades to the ground over the outer fifth of the *displayed* radius, so the compressed buffer still meets the ground cleanly."""
    radius = coverage_radius()
    return 1 - smoothstep(np.hypot(*display_map(x, y)), radius * .80, radius)


def relief_scale(x, y):
    """Vertical scale that follows the warp's local horizontal scale (capped at 1), so the compressed buffer keeps natural slopes instead of cliffs."""
    wx, wy = display_map(x, y)
    det = (np.gradient(wx, axis=1) * np.gradient(wy, axis=0) - np.gradient(wx, axis=0) * np.gradient(wy, axis=1)) / (np.gradient(x, axis=1) * np.gradient(y, axis=0))
    return np.clip(np.sqrt(np.abs(det)), 0, 1)


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
    """Map radial distance to a sphere whose cap of half-angle CAP_ANGLE stands above z=0."""
    radius = coverage_radius(); alpha = CAP_ANGLE; sphere = (SPAN / 2) / math.sin(alpha)
    x, y = display_map(x, y)
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
    dem = source / 'dem.tif'; rivers = source / 'rivers.json'
    if not dem.exists():
        params = dict(bbox='-115,31,-96,47', bboxSR=4326, imageSR=4326, size='2048,2048', format='tiff', pixelType='F32', noData=-999999, interpolation='RSP_BilinearInterpolation', renderingRule=json.dumps({'rasterFunction':'None'}), f='json')
        url = DEM_SERVICE + '?' + urlencode(params)
        info = read_json(url); payload = urlopen(info['href'], timeout=240).read()
        temp = dem.with_suffix('.part'); temp.write_bytes(payload)
        with rasterio.open(temp) as src:
            if src.count != 1 or src.dtypes[0] != 'float32': raise ValueError('Expected raw float32 elevation')
        temp.replace(dem); (source / 'dem-request.json').write_text(json.dumps({'url':url, 'response':info}, indent=2))
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
    broad = gaussian_filter(true, 12)
    rounded = gaussian_filter(true, 3)
    return np.maximum(broad - DATUM_M, 0) * scale * GAIN + (rounded - broad) * scale * FINE_GAIN


def author(root, n):
    dem_path, features = fetch_sources(root); checks = geographic_checks(features)
    radius = coverage_radius(); px = 2 * radius / (n - 1); scale = SPAN / (2 * radius)
    x, y = np.meshgrid(np.linspace(-radius, radius, n), np.linspace(radius, -radius, n))
    lon, lat = transform(CRS, 'EPSG:4326', x.ravel(), y.ravel())
    with rasterio.open(dem_path) as src:
        data = src.read(1); lon, lat = np.array(lon), np.array(lat)
        cols = (lon - src.transform.c) / src.transform.a - .5; rows = (lat - src.transform.f) / src.transform.e - .5
        true = map_coordinates(data, [rows, cols], order=1, mode='nearest').reshape(n, n)
    if not np.isfinite(true).all() or true.min() < -1000: raise ValueError('DEM contains missing elevations')
    true = gaussian_filter(true, 1.25)
    shapes = []; river_features = []
    for f in features:
        name = f['attributes']['GNIS_NAME']; half_width = RIVER_HALF_WIDTH_M['major' if name in MAJOR_RIVERS else 'other']
        for path in f['geometry']['paths']:
            xy = np.column_stack(project(*np.array(path).T))
            if xy[:, 0].max() < -radius or xy[:, 0].min() > radius or xy[:, 1].max() < -radius or xy[:, 1].min() > radius: continue
            shapes.append((LineString(xy), half_width))
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
    d = np.hypot(x,y); positions = cap_positions(x, y, maps['height'] * rim_taper(x, y) * relief_scale(x, y))
    ids = np.arange(n*n).reshape(n,n)
    faces = np.stack([ids[:-1,:-1], ids[1:,:-1], ids[1:,1:], ids[:-1,1:]], axis=-1)
    valid = d <= radius; faces = faces[valid[:-1,:-1] & valid[1:,:-1] & valid[1:,1:] & valid[:-1,1:]]
    used, inv = np.unique(faces, return_inverse=True)
    np.savez(root / 'model.npz', positions=positions.reshape(-1,3)[used].astype('float32'), faces=inv.reshape(-1,4).astype('int32'), color=maps['base_color'].reshape(-1,3)[used].astype('float32'), roughness=maps['roughness'].ravel()[used], xy=np.stack([x,y],-1).reshape(-1,2)[used], source_height=true.ravel()[used])
    np.savez(root / 'geography.npz', height=true, styled_height=maps['height'], snow=snow, bank_m=bank_m, channel=maps['channel'])
    (root / 'rivers.geojson').write_text(json.dumps({'type':'FeatureCollection','features':river_features}))
    # Border is a separate toggleable geographic guide, draped on exactly the same surface.
    border = []
    for a,b in [((-109.05,37),(-102.05,37)),((-102.05,37),(-102.05,41)),((-102.05,41),(-109.05,41)),((-109.05,41),(-109.05,37))]:
        coords = np.linspace(a,b,250); bx,by = project(coords[:,0],coords[:,1]); h = map_coordinates(maps['height'] * rim_taper(x, y) * relief_scale(x, y),[(radius-by)/px,(bx+radius)/px],order=1)
        border.extend(cap_positions(bx,by,h+.0015).tolist())
    (root / 'border.json').write_text(json.dumps(border))
    crossings_xyz = {name: cap_positions(*project(np.array(pts)[:,0], np.array(pts)[:,1]), map_coordinates(maps['height'], [(radius-project(np.array(pts)[:,0], np.array(pts)[:,1])[1])/px, (project(np.array(pts)[:,0], np.array(pts)[:,1])[0]+radius)/px], order=1)).tolist() for name, pts in checks.items()}
    manifest = {'name':'Colorado crown', 'lods':1, 'resolution':n, 'axes':'source Z up, +X east, +Y north; GLB Y up, north -Z', 'units':'model metres', 'map_crs':CRS, 'map_radius_m':radius, 'buffer_miles':200, 'coverage':'Circular extent enclosing Colorado corners plus 321868.8 metres in the local equidistant projection; extra 2 km margin', 'cap_half_angle_degrees':math.degrees(CAP_ANGLE), 'sphere_exposed_diameter_fraction':(1-math.cos(CAP_ANGLE))/2, 'display_warp':{'focus_normalized':list(WARP_FOCUS),'radial_focus':WARP_RADIAL,'rim_taper':'relief fades over display radius .80R..R','note':'State enlarged across crown, eastern plains wrapped onto the right shoulder; terrain, channels, snow and geographic guides share the warp'}, 'water_linear':WATER_LINEAR, 'water_tone':WATER_TONE, 'water_roughness':WATER_ROUGHNESS, 'span_m':SPAN, 'vertical_gain':{'broad_landforms':GAIN,'fine_relief':FINE_GAIN,'broad_smoothing_grid_pixels':12,'fine_smoothing_grid_pixels':3}, 'height_datum_m':DATUM_M, 'river_full_width_m':{k:2*v for k,v in RIVER_HALF_WIDTH_M.items()}, 'major_rivers':MAJOR_RIVERS, 'bank_scale':BANK_SCALE, 'channel_bed':'recipe bed cut below the sculpted height of the nearest channel cell', 'sources':{'elevation':DEM_SERVICE,'hydrography':HYDRO_SERVICE,'hashes':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [dem_path,root/'source/rivers.json']}}, 'border_crossings_lon_lat':checks, 'border_crossings_model_xyz':crossings_xyz, 'rim_taper_display_fraction':[.80,1.0], 'relief_scale':'heights multiplied by min(1, local linear scale of the display warp)', 'style':'Shared relief_study.style_surface recipe, softened DEM, true-height patchy snow, continuous narrow mapped channels in the shared San Luis water palette; widths and spherical curvature are artistic exaggerations', 'vertices':len(used),'quads':len(faces)}
    (root / 'manifest.json').write_text(json.dumps(manifest,indent=2))
    review_map(root, features, true, bank_m, radius, checks)
    print(json.dumps({'vertices':len(used),'crossings':checks}),flush=True)


def review_map(root, features, dem, bank, radius, checks):
    from PIL import Image, ImageDraw
    n = dem.shape[0]; tone = smoothstep(dem,500,4300)
    color = np.stack([.85-.45*tone,.78-.40*tone,.62-.30*tone],-1); color[bank<0] = [.38,.62,.72]
    image = Image.fromarray(np.uint8(color*255)).resize((1400,1400)); draw = ImageDraw.Draw(image)
    def pixels(coords):
        xy = np.column_stack(project(*np.array(coords).T)); return [tuple(p) for p in np.column_stack([(xy[:,0]+radius)/(2*radius)*1400,(radius-xy[:,1])/(2*radius)*1400])]
    for a,b in [((-109.05,37),(-102.05,37)),((-102.05,37),(-102.05,41)),((-102.05,41),(-109.05,41)),((-109.05,41),(-109.05,37))]: draw.line(pixels(np.linspace(a,b,200)),fill='white',width=3)
    for name, points in checks.items():
        for px_,py_ in pixels(points):
            draw.ellipse((px_-7,py_-7,px_+7,py_+7),fill='red'); draw.text((px_+12,py_),name,fill='black',stroke_width=1,stroke_fill='white')
    draw.text((24,24),'SOURCE MAP / NORTH UP / white = Colorado / red = verified border crossings',fill='black')
    image.save(root/'geography-review.png')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output',type=Path,required=True); parser.add_argument('--resolution',type=int,default=1537)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True); author(args.output,args.resolution)
