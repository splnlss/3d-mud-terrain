"""Region-wide vector sources for relief tiles, cached under the tileset's work folder in UTM metres.

Hydrography comes from the project's NHD extract; roads and buildings from OpenStreetMap.
"""
import json
import pickle
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import numpy as np
import rasterio
from rasterio.warp import transform, transform_bounds
from shapely.geometry import shape
from shapely.ops import transform as shapely_transform

OVERPASS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter']


def region_frame(dem_path):
    """CRS and node-registered square (west, north, size) of the regional DEM."""
    with rasterio.open(dem_path) as src:
        size = (min(src.width, src.height) - 1) * src.res[0]
        return str(src.crs), src.bounds.left + src.res[0] / 2, src.bounds.top - src.res[0] / 2, size


def overpass(query):
    for attempt, host in enumerate(OVERPASS * 3):
        try:
            request = Request(host, data=urlencode({'data': query}).encode(), headers={'User-Agent': 'san-luis-relief-bake'})
            return json.loads(urlopen(request, timeout=300).read())['elements']
        except OSError:
            time.sleep(5 * (attempt + 1))
    raise RuntimeError('OpenStreetMap Overpass servers unavailable; retry')


def load_sources(dem_path, hydro_path, work):
    """Dict of hydro lines, waterbodies, roads and buildings in UTM; downloaded and converted once."""
    cache = Path(work) / 'region-sources.pkl'
    if cache.exists(): return pickle.loads(cache.read_bytes())
    crs, west, north, size = region_frame(dem_path); hydro = json.loads(Path(hydro_path).read_text())
    to_utm = lambda xs, ys: transform('EPSG:4326', crs, list(xs), list(ys))
    lines = []
    for feature in hydro['layers']['6']:
        geometry = feature['geometry']; parts = [geometry['coordinates']] if geometry['type'] == 'LineString' else geometry['coordinates']
        for part in parts:
            x, y = to_utm([p[0] for p in part], [p[1] for p in part]); p = feature['properties']
            lines.append({'xy': np.column_stack([x, y]), 'visibility': p['visibilityfilter'], 'ftype': p['ftype'], 'name': p.get('gnis_name')})
    lakes = []
    for feature in hydro['layers']['12']:
        if feature['properties']['ftype'] not in (390, 436): continue  # lakes, ponds and reservoirs
        polygon = shapely_transform(lambda x, y, z=None: to_utm(np.atleast_1d(x), np.atleast_1d(y)), shape(feature['geometry']))
        lakes.append({'polygon': polygon, 'area_m2': polygon.area, 'bounds': polygon.bounds})
    s, w_, n, e = None, None, None, None
    w_, s, e, n = transform_bounds(crs, 'EPSG:4326', west, north - size, west + size, north)
    roads, buildings = [], []
    # Quadrants keep each public-server query small.
    for i in range(2):
        for j in range(2):
            box = f'{s + (n - s) * j / 2},{w_ + (e - w_) * i / 2},{s + (n - s) * (j + 1) / 2},{w_ + (e - w_) * (i + 1) / 2}'
            ways = overpass(f'[out:json][timeout:240];way["highway"~"^(motorway|trunk|primary|secondary|tertiary|unclassified|residential|service|track)(_link)?$"]({box});out geom;')
            for way in ways:
                x, y = to_utm([p['lon'] for p in way['geometry']], [p['lat'] for p in way['geometry']])
                roads.append({'id': way['id'], 'xy': np.column_stack([x, y]), 'highway': way['tags']['highway'].replace('_link', '')})
            for item in overpass(f'[out:json][timeout:240];way["building"]({box});out center;'):
                buildings.append((item['id'], item['center']['lon'], item['center']['lat']))
    roads = list({road['id']: road for road in roads}.values()); buildings = list({b[0]: b for b in buildings}.values())
    bx, by = to_utm([b[1] for b in buildings], [b[2] for b in buildings]) if buildings else ([], [])
    sources = {'crs': crs, 'lines': lines, 'lakes': lakes, 'roads': roads, 'buildings': np.column_stack([bx, by]) if buildings else np.zeros((0, 2)),
        'attribution': 'USGS NHD; OpenStreetMap contributors (ODbL)'}
    Path(work).mkdir(parents=True, exist_ok=True); cache.write_bytes(pickle.dumps(sources))
    return sources


def region_mosaic(dem_path, work, pixel_m=20, chunks=4):
    """True-colour NAIP for the whole region at `pixel_m`, fetched in chunks and cached."""
    from PIL import Image
    path = Path(work) / f'region-naip-{pixel_m}m.jpg'
    if path.exists(): return np.asarray(Image.open(path).convert('RGB'))
    crs, west, north, size = region_frame(dem_path); n = int(size / pixel_m / chunks); epsg = crs.split(':')[1]; step = size / chunks
    mosaic = np.zeros((n * chunks, n * chunks, 3), 'uint8')
    for j in range(chunks):
        for i in range(chunks):
            box = f'{west + i * step},{north - (j + 1) * step},{west + (i + 1) * step},{north - j * step}'
            url = ('https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage'
                   f'?bbox={box}&bboxSR={epsg}&imageSR={epsg}&size={n},{n}&format=jpg&bandIds=0,1,2&f=image')
            for attempt in range(6):
                try:
                    data = urlopen(url, timeout=240).read()
                    if data[:1] not in (b'<', b'{'): break
                except OSError: pass
                time.sleep(8 * (attempt + 1))
            else: raise RuntimeError('NAIP imagery unavailable for the region mosaic')
            import io
            mosaic[j * n:(j + 1) * n, i * n:(i + 1) * n] = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    Image.fromarray(mosaic).save(path, quality=90); return mosaic


def detect_pivots(mosaic, pixel_m=20, radii_m=(200, 280, 360, 400, 440), completeness=.62):
    """Centre-pivot fields as rows of (column, row, radius in pixels, mean brightness 0..1).

    A pivot is a circle whatever its crop or season, so it is found by its outline: the share
    of a ring of the right radius that lies on an image edge.
    """
    from scipy.ndimage import gaussian_filter, maximum_filter
    from scipy.signal import fftconvolve
    image = gaussian_filter(mosaic.astype('float32'), (1, 1, 0)); edge = np.zeros(image.shape[:2], 'float32')
    for band in range(3):
        gy, gx = np.gradient(image[..., band]); edge = np.maximum(edge, np.hypot(gx, gy))
    strong = (edge > np.maximum(2.2, .9 * gaussian_filter(edge, 12))).astype('float32'); best = np.zeros_like(edge); which = np.zeros_like(edge)
    for radius_m in radii_m:
        r = radius_m / pixel_m; k = int(r) + 3; yy, xx = np.mgrid[-k:k + 1, -k:k + 1]; d = np.hypot(xx, yy)
        ring = (np.abs(d - r) < 1.0).astype('float32'); inner = (d < r - 2.5).astype('float32')
        share = fftconvolve(strong, ring / ring.sum(), mode='same')
        clutter = fftconvolve(strong, inner / inner.sum(), mode='same')  # a pivot's interior is plain
        score = share - .8 * clutter; better = score > best; best = np.where(better, score, best); which = np.where(better, r, which)
    # Small rings match by chance more easily, so they must be more complete.
    peak = (best == maximum_filter(best, size=int(1.5 * min(radii_m) / pixel_m))) & (best > np.where(which < 300 / pixel_m, completeness + .12, completeness))
    rows, cols = np.nonzero(peak); order = np.argsort(-best[rows, cols]); kept = []
    for i in order:  # strongest first; no overlapping discs
        if all(np.hypot(cols[i] - c, rows[i] - r) > .9 * (which[rows[i], cols[i]] + rr) for c, r, rr, _ in kept):
            rr = which[rows[i], cols[i]]; yy, xx = np.ogrid[-int(rr):int(rr) + 1, -int(rr):int(rr) + 1]
            r0, c0 = rows[i], cols[i]
            if r0 - int(rr) < 0 or c0 - int(rr) < 0 or r0 + int(rr) + 1 > edge.shape[0] or c0 + int(rr) + 1 > edge.shape[1]: continue
            disc = image[r0 - int(rr):r0 + int(rr) + 1, c0 - int(rr):c0 + int(rr) + 1].mean(2)[np.hypot(xx, yy) < rr * .85]
            kept.append((cols[i], rows[i], rr, float(disc.mean() / 255)))
    return np.array(kept).reshape(-1, 4)


def region_pivots(dem_path, work):
    """Centre pivots in UTM as rows of (x, y, radius m, brightness 0..1), kept only on level ground."""
    cache = Path(work) / 'region-pivots.npy'
    if cache.exists(): return np.load(cache)
    crs, west, north, size = region_frame(dem_path); found = detect_pivots(region_mosaic(dem_path, work))
    with rasterio.open(dem_path) as src:
        dem = src.read(1, out_shape=(src.height // 10, src.width // 10)); gy, gx = np.gradient(dem, 100.0); slope = np.hypot(gx, gy)
    x = west + (found[:, 0] + .5) * 20; y = north - (found[:, 1] + .5) * 20
    level = slope[np.clip(((north - y) / 100).astype(int), 0, slope.shape[0] - 1), np.clip(((x - west) / 100).astype(int), 0, slope.shape[1] - 1)] < .03
    pivots = np.column_stack([x, y, found[:, 2] * 20, found[:, 3]])[level]; np.save(cache, pivots); return pivots
