"""Irrigation ditch and acequia map for the relief region.

Ditch lines come from USGS NHD (canal/ditch flowlines). Headgates, names and water-right priority dates come
from the Colorado Division of Water Resources (CDSS) REST API. Each headgate is joined to the nearest ditch line
so lines carry a name and earliest appropriation date where one is known.

Acequias are flagged by an approximation: Costilla and Conejos county ditches whose earliest right predates
1880, or whose name says ACEQUIA. Colorado recognises acequias by their governance, not by date, so treat the
flag as a guide; New Mexico ditches (south of the state line) have no CDSS record and carry NHD names only.

    uv run python -m bake.style.ditches --output data/ditches
"""
import argparse
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
import numpy as np
from rasterio.warp import transform, transform_bounds
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw
from bake.style.region_sources import load_sources, region_frame, region_mosaic
from bake.style.relief_patch import densify

DEM = 'data/san-luis-112640-10.tif'; HYDRO = 'data/nhd-112640.json'
CDSS = 'https://dwr.state.co.us/Rest/GET/api/v2'
ACEQUIA_COUNTIES = {'COSTILLA', 'CONEJOS'}; ACEQUIA_BEFORE = '1880'; JOIN_M = 400
SAN_LUIS = (-105.4239, 37.2008)


def cdss(path, **query):
    """Every record of a CDSS endpoint for the query, cached by the caller."""
    rows, page = [], 1
    while True:
        data = json.loads(urlopen(f'{CDSS}/{path}/?' + urlencode({'format': 'json', 'pageSize': 50000, 'pageIndex': page, **query}), timeout=300).read())
        rows += data.get('ResultList', []); page += 1
        if page > data.get('PageCount', 1): return rows


def build(output, work):
    output, work = Path(output), Path(work); output.mkdir(parents=True, exist_ok=True)
    crs, west, north, size = region_frame(DEM); lon0, lat0, lon1, lat1 = transform_bounds(crs, 'EPSG:4326', west, north - size, west + size, north)
    near = dict(latitude=(lat0 + lat1) / 2, longitude=(lon0 + lon1) / 2, radius=55, units='miles')
    cache = work / 'cdss-ditches.json'
    if not cache.exists():
        cache.write_text(json.dumps({'structures': cdss('structures', structureType='DITCH', **near), 'rights': cdss('waterrights/netamount', **near)}))
    raw = json.loads(cache.read_text())
    first = {}
    for right in raw['rights']:
        date = (right.get('appropriationDate') or '')[:10]
        if date and (right['wdid'] not in first or date < first[right['wdid']]): first[right['wdid']] = date
    gates = []
    for s in raw['structures']:
        if s.get('structureType') != 'DITCH': continue  # the API ignores its type filter for distance queries
        lon, lat = s.get('longdecdeg'), s.get('latdecdeg')
        if lon is None or lat is None or not (lon0 <= lon <= lon1 and lat0 <= lat <= lat1): continue
        name = (s.get('structureName') or '').strip(); date = first.get(s['wdid'])
        acequia = s.get('county') in ACEQUIA_COUNTIES and (bool(date) and date < ACEQUIA_BEFORE or 'ACEQUIA' in name)
        gates.append({'wdid': s['wdid'], 'name': name, 'source': s.get('waterSource'), 'county': s.get('county'), 'appropriated': date, 'status': {'A': 'active', 'H': 'historical', 'I': 'inactive', 'N': 'never built'}.get(s.get('ciuCode'), 'unknown'),
                      'acequia': bool(acequia), 'lon': lon, 'lat': lat})
    gx, gy = transform('EPSG:4326', crs, [g['lon'] for g in gates], [g['lat'] for g in gates])
    lines = [l for l in load_sources(DEM, HYDRO, work)['lines'] if l['ftype'] == 336]
    # Join each headgate to the nearest ditch line within JOIN_M; a line keeps its oldest headgate.
    points = [densify(l['xy'], 20) for l in lines]; owner = np.concatenate([np.full(len(p), i) for i, p in enumerate(points)])
    dist, idx = cKDTree(np.concatenate(points)).query(np.column_stack([gx, gy]))
    best = {}
    for g, d, i in zip(gates, dist, idx):
        if d > JOIN_M: continue
        line = owner[i]
        if line not in best or (g['appropriated'] or '9') < (best[line]['appropriated'] or '9'): best[line] = g
    features = []
    for i, line in enumerate(lines):
        lon, lat = transform(crs, 'EPSG:4326', line['xy'][:, 0], line['xy'][:, 1]); g = best.get(i, {})
        name = line['name'] or g.get('name')
        acequia = bool(g.get('acequia')) or 'acequia' in (line['name'] or '').lower()
        features.append({'type': 'Feature', 'geometry': {'type': 'LineString', 'coordinates': [[round(a, 6), round(b, 6)] for a, b in zip(lon, lat)]},
            'properties': {'name': name, 'nhd_name': line['name'], 'wdid': g.get('wdid'), 'appropriated': g.get('appropriated'), 'acequia': acequia,
                           'headgate_distance_m': round(float(dist[gates.index(g)]), 1) if g else None}})
    # NHD splits a ditch into many segments; one headgate only reaches the nearest. Segments sharing a name share the flag and date.
    named = {}
    for f in features:
        p = f['properties']
        if p['name'] and p['acequia']: named.setdefault(p['name'], p)
    for f in features:
        p = f['properties']
        if p['name'] in named and not p['acequia']: p.update(acequia=True, appropriated=p['appropriated'] or named[p['name']]['appropriated'])
    attribution = 'USGS National Hydrography Dataset; Colorado Division of Water Resources (CDSS)'
    (output / 'ditches.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'attribution': attribution, 'features': features}))
    (output / 'headgates.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'attribution': attribution, 'features': [
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [g['lon'], g['lat']]}, 'properties': {k: v for k, v in g.items() if k not in ('lon', 'lat')}} for g in gates]}))
    draw_maps(output, work, lines, features, gates, gx, gy)
    km = lambda fs: round(sum(np.hypot(*np.diff(lines[i]['xy'], axis=0).T).sum() for i, f in enumerate(features) if f in fs) / 1000)
    summary = {'ditch_lines': len(features), 'ditch_km': km(features), 'acequia_lines': sum(f['properties']['acequia'] for f in features),
               'acequia_km': km([f for f in features if f['properties']['acequia']]), 'named_lines': sum(bool(f['properties']['name']) for f in features),
               'headgates': len(gates), 'acequia_headgates': sum(g['acequia'] for g in gates), 'attribution': attribution,
               'acequia_rule': f'{sorted(ACEQUIA_COUNTIES)} county ditch with first right before {ACEQUIA_BEFORE}, or ACEQUIA in its name'}
    (output / 'ditches.json').write_text(json.dumps(summary, indent=1) + '\n'); return summary


def draw_maps(output, work, lines, features, gates, gx, gy):
    """A region map and a San Luis close-up over 20 m aerial imagery: blue ditches, red acequias, dots for headgates."""
    crs, west, north, size = region_frame(DEM); mosaic = region_mosaic(DEM, work); px = size / mosaic.shape[0]
    sx, sy = transform('EPSG:4326', crs, [SAN_LUIS[0]], [SAN_LUIS[1]])
    for name, (cx, cy, half, out) in {'ditches-region': (west + size / 2, north - size / 2, size / 2, 2400),
                                      'ditches-san-luis': (sx[0], sy[0], 9000, 2000)}.items():
        c0, r0 = int((cx - half - west) / px), int((north - cy - half) / px); c1, r1 = int((cx + half - west) / px), int((north - cy + half) / px)
        image = Image.fromarray(mosaic[max(r0, 0):r1, max(c0, 0):c1]).resize((out, out), Image.LANCZOS)
        image = Image.blend(image, Image.new('RGB', image.size, (255, 255, 255)), .35); draw = ImageDraw.Draw(image)
        to = lambda x, y: ((x - (cx - half)) / (2 * half) * out, ((cy + half) - y) / (2 * half) * out)
        width = 2 if half > 20000 else 4
        for acequia_pass in (False, True):
            for line, f in zip(lines, features):
                if f['properties']['acequia'] != acequia_pass: continue
                draw.line([to(x, y) for x, y in line['xy']], fill=(200, 30, 30) if acequia_pass else (20, 90, 210), width=width + acequia_pass)
        for g, x, y in zip(gates, gx, gy):
            u, v = to(x, y); r = 2 if half > 20000 else 4
            if 0 <= u < out and 0 <= v < out: draw.ellipse((u - r, v - r, u + r, v + r), fill=(200, 30, 30) if g['acequia'] else (20, 90, 210), outline=(255, 255, 255))
        if half < 20000:
            for line, f in zip(lines, features):
                p = f['properties']
                if p['acequia'] and p['name'] and len(line['xy']) > 3:
                    u, v = to(*line['xy'][len(line['xy']) // 2])
                    if 0 <= u < out and 0 <= v < out: draw.text((u + 6, v - 6), f"{p['name'].title()} {(p['appropriated'] or '')[:4]}", fill=(120, 0, 0))
        draw.text((12, out - 22), 'Blue: ditches and canals (USGS NHD). Red: acequias (approximate). Dots: headgates (Colorado DWR).', fill=(0, 0, 0))
        image.save(output / f'{name}.jpg', quality=88)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work', type=Path, default=Path('/Volumes/TXX_Backup/DustnDivide/05_3D-tiles/relief-tiles-sample/work'))
    args = parser.parse_args(); print(json.dumps(build(args.output, args.work), indent=1))
