"""Cultivated parcels read from aerial imagery, so farmland mirrors the real field pattern.

Input is a colour-infrared NAIP export (bands NIR, red, green) covering the patch
square, row zero north. Parcels are irrigated, evenly textured ground split along
visible boundaries. Row direction comes from the imagery's own mowing or tilling
lines; near-circular parcels are treated as centre pivots with concentric rows.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen
import numpy as np
from scipy.ndimage import binary_closing, binary_dilation, binary_opening, gaussian_filter, label, uniform_filter
from PIL import Image

NAIP = 'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage'


def fetch_naip(package, output, pixels=1400):
    """Download true-colour and colour-infrared NAIP for the package's patch square, with provenance."""
    m = json.loads((Path(package) / 'manifest.json').read_text()); cx, cy = m['origin_utm_m']; half = m['size_m'] / 2
    output = Path(output); output.mkdir(parents=True, exist_ok=True); record = {'service': NAIP, 'crs': m['source_crs'], 'files': {}}
    box = f'{cx - half},{cy - half},{cx + half},{cy + half}'; epsg = m['source_crs'].split(':')[1]
    for name, bands, kind in [('naip.jpg', '0,1,2', 'jpg'), ('naip-cir.png', '3,0,1', 'png')]:
        url = f'{NAIP}?bbox={box}&bboxSR={epsg}&imageSR={epsg}&size={pixels},{pixels}&format={kind}&bandIds={bands}&f=image'
        data = urlopen(url, timeout=180).read()
        if data[:1] == b'<': raise RuntimeError(f'NAIP service returned an error page for {name}; retry')
        (output / name).write_bytes(data); record['files'][name] = {'url': url, 'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'naip.json').write_text(json.dumps(record, indent=2) + '\n')


def woody_cover(cir):
    """Tree and shrub cover 0..1 from colour-infrared imagery: green in infrared and rough in texture."""
    cir = np.asarray(cir, float); nir, red = cir[..., 0], cir[..., 1]; ndvi = (nir - red) / (nir + red + 1e-6); grey = cir.mean(2)
    rough = np.sqrt(np.clip(uniform_filter(grey ** 2, 7) - uniform_filter(grey, 7) ** 2, 0, None))
    t = lambda v, lo, hi: np.clip((v - lo) / (hi - lo), 0, 1)
    return t(gaussian_filter(ndvi, 1.5), .15, .38) * t(gaussian_filter(rough, 2), 11, 24)


def field_parcels(cir, size_m, min_area_m2=9000, ndvi_min=.2, texture_max=14, pixel_m=None):
    """Parcel id raster (0 = none) and per-parcel records: row direction, pivot centre, tone.

    Tuned on 1.4 m pixels. With `pixel_m` above 3 m the texture test no longer separates crops from
    forest, so farmland is green in infrared and bright in visible light, and filters shrink to match.
    """
    cir = np.asarray(cir, float); px = size_m / cir.shape[0]; coarse = pixel_m is not None and pixel_m > 3
    nir, red = cir[..., 0], cir[..., 1]; ndvi = (nir - red) / (nir + red + 1e-6); lum = cir.mean(2)
    if coarse:
        farmed = (gaussian_filter(ndvi, .8) > .22) & (gaussian_filter(cir[..., 1:].mean(2), .8) > 62)
        farmed = binary_closing(binary_opening(farmed, iterations=2), iterations=1); min_area_m2 = max(min_area_m2, (9 * px) ** 2)
        soft = gaussian_filter(cir, (1.0, 1.0, 0)); edge_level, shrink, grow = 9.0, 1, 2
    else:
        texture = np.sqrt(np.clip(uniform_filter(lum ** 2, 7) - uniform_filter(lum, 7) ** 2, 0, None))
        farmed = (gaussian_filter(ndvi, 2) > ndvi_min) & (gaussian_filter(texture, 5) < texture_max)
        farmed = binary_closing(binary_opening(farmed, iterations=5), iterations=3)
        soft = gaussian_filter(cir, (2.5, 2.5, 0)); edge_level, shrink, grow = 3.2, 3, 4
    # Parcel boundaries: fences, ditches, roads and crop changes show as edges in the smoothed image.
    edge = np.zeros(lum.shape)
    for band in range(3):
        gy, gx = np.gradient(soft[..., band]); edge = np.maximum(edge, np.hypot(gx, gy))
    regions, count = label(binary_opening(farmed & ~binary_dilation(edge > edge_level, iterations=1), iterations=shrink))
    rows, cols = np.mgrid[0:lum.shape[0], 0:lum.shape[1]]
    lines = lum - gaussian_filter(lum, 3); gy, gx = np.gradient(gaussian_filter(lines, 1))
    ids = np.zeros(lum.shape, 'int32'); parcels = []
    for region in range(1, count + 1):
        mask = regions == region; area = mask.sum() * px * px
        if area < min_area_m2: continue
        grown = binary_dilation(mask, iterations=grow) & farmed & (ids == 0)  # reclaim the eroded boundary strip
        r, c = rows[grown], cols[grown]; cr, cc = r.mean(), c.mean()
        jxx, jyy, jxy = (gx[mask] ** 2).mean(), (gy[mask] ** 2).mean(), (gx[mask] * gy[mask]).mean()
        coherence = np.hypot(jxx - jyy, 2 * jxy) / (jxx + jyy + 1e-9)
        angle = .5 * np.arctan2(2 * jxy, jxx - jyy)  # direction across the rows
        if coherence < .12:
            # No visible rows: run them along the parcel's long axis.
            cov = np.cov(np.stack([c - cc, r - cr])); values, vectors = np.linalg.eigh(cov)
            angle = np.arctan2(vectors[1, 0], vectors[0, 0])
        radius = np.hypot(r - cr, c - cc).max(); circular = grown.sum() / (np.pi * radius ** 2)
        ids[grown] = len(parcels) + 1
        parcels.append({'area_m2': float(area), 'centre_px': [float(cc), float(cr)], 'row_normal_rad': float(angle),
            'row_coherence': float(coherence), 'pivot': bool(circular > .78), 'tone': float(np.clip((lum[mask].mean() - 90) / 80, 0, 1))})
    return ids, parcels


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package', type=Path, default=Path('data/style-patch'))
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    fetch_naip(args.package, args.output); print(len(fetch_roads(args.package, args.output)), 'roads')
    if os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ.get('NEXT_PUBLIC_GOOGLE_MAPS_TOKEN'): fetch_google(args.package, args.output)


def patch_square(package):
    m = json.loads((Path(package) / 'manifest.json').read_text()); cx, cy = m['origin_utm_m']; half = m['size_m'] / 2
    return m['source_crs'], (cx - half, cy - half, cx + half, cy + half)


def fetch_google(package, output, zoom=17, pixels=1400):
    """Google satellite tiles for the patch square, warped to the patch grid. Key comes from the environment."""
    import io, math, os
    from urllib.request import Request
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject, transform_bounds
    key = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ['NEXT_PUBLIC_GOOGLE_MAPS_TOKEN']
    crs, bounds = patch_square(package); west, south, east, north = transform_bounds(crs, 'EPSG:4326', *bounds)
    request = Request(f'https://tile.googleapis.com/v1/createSession?key={key}', method='POST', headers={'Content-Type': 'application/json'},
        data=json.dumps({'mapType': 'satellite', 'language': 'en-US', 'region': 'US'}).encode())
    session = json.loads(urlopen(request, timeout=60).read())['session']
    tile = lambda lon, lat: (int((lon + 180) / 360 * 2 ** zoom), int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * 2 ** zoom))
    (x0, y0), (x1, y1) = tile(west, north), tile(east, south)
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256, 3), 'uint8')
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            data = urlopen(f'https://tile.googleapis.com/v1/2dtiles/{zoom}/{tx}/{ty}?session={session}&key={key}', timeout=60).read()
            mosaic[(ty - y0) * 256:(ty - y0 + 1) * 256, (tx - x0) * 256:(tx - x0 + 1) * 256] = np.asarray(Image.open(io.BytesIO(data)).convert('RGB'))
    world = 20037508.342789244; span = 2 * world / 2 ** zoom
    source = from_bounds(-world + x0 * span, world - (y1 + 1) * span, -world + (x1 + 1) * span, world - y0 * span, mosaic.shape[1], mosaic.shape[0])
    warped = np.zeros((3, pixels, pixels), 'uint8')
    reproject(mosaic.transpose(2, 0, 1), warped, src_transform=source, src_crs='EPSG:3857',
        dst_transform=from_bounds(*bounds, pixels, pixels), dst_crs=crs, resampling=Resampling.bilinear)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    Image.fromarray(warped.transpose(1, 2, 0)).save(output / 'google-satellite.jpg', quality=92)
    (output / 'google-satellite.json').write_text(json.dumps({'service': 'Google Map Tiles API, satellite 2D tiles', 'zoom': zoom,
        'tiles': [x0, y0, x1, y1], 'crs': crs, 'note': 'Local working copy under Google Maps Platform terms; do not redistribute.'}, indent=2) + '\n')


def fetch_roads(package, output):
    """Roads and tracks crossing the patch square, in patch metres (x east, z south).

    OpenStreetMap is taken whole; USGS National Map and Census TIGER local roads add the
    stretches OpenStreetMap lacks (anything further than 35 m from an OpenStreetMap line).
    """
    from urllib.parse import urlencode
    from urllib.request import Request
    from rasterio.warp import transform, transform_bounds
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    crs, bounds = patch_square(package); west, south, east, north = transform_bounds(crs, 'EPSG:4326', *bounds)
    query = f'[out:json][timeout:60];way["highway"]({south},{west},{north},{east});out geom;'
    ways = None
    for host in ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'] * 2:  # public servers shed load
        try:
            request = Request(host, data=urlencode({'data': query}).encode(), headers={'User-Agent': 'san-luis-relief-bake'})
            ways = json.loads(urlopen(request, timeout=120).read())['elements']; break
        except OSError: continue
    if ways is None: raise RuntimeError('OpenStreetMap Overpass servers unavailable; retry')
    cx, cy = (bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2; features = []
    for way in ways:
        xs, ys = transform('EPSG:4326', crs, [p['lon'] for p in way['geometry']], [p['lat'] for p in way['geometry']])
        features.append({'type': 'Feature', 'properties': {'source': 'osm', 'osm_id': way['id'], 'highway': way['tags'].get('highway'), 'name': way['tags'].get('name')},
            'geometry': {'type': 'LineString', 'coordinates': [[x - cx, cy - y] for x, y in zip(xs, ys)]}})
    known = unary_union([LineString(f['geometry']['coordinates']) for f in features]).buffer(35)
    epsg = crs.split(':')[1]
    for source, service in [('usgs', 'https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/32'),
                            ('tiger', 'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Transportation/MapServer/8')]:
        params = urlencode({'geometry': ','.join(map(str, bounds)), 'geometryType': 'esriGeometryEnvelope', 'inSR': epsg, 'outSR': epsg,
            'spatialRel': 'esriSpatialRelIntersects', 'outFields': '*', 'f': 'geojson'})
        for item in json.loads(urlopen(f'{service}/query?{params}', timeout=180).read()).get('features', []):
            g = item['geometry']; parts = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
            for part in parts:
                extra = LineString([(x - cx, cy - y) for x, y, *_ in part]).difference(known)
                for piece in getattr(extra, 'geoms', [extra]):
                    if piece.is_empty or piece.length < 90: continue
                    features.append({'type': 'Feature', 'properties': {'source': source, 'highway': 'unclassified', 'name': None},
                        'geometry': {'type': 'LineString', 'coordinates': [list(c) for c in piece.coords]}})
                    known = known.union(piece.buffer(35))
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    (output / 'roads.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'source': 'OpenStreetMap contributors (ODbL) via Overpass API; USGS National Map transportation; US Census TIGERweb',
        'features': features}) + '\n')
    return features
