"""Finer terrain for the patch from Google Photorealistic 3D Tiles.

Walks the tileset down to tiles covering the patch square, decodes their meshes and
rasterises the surface onto the patch grid (metres above the ellipsoid; row zero north).
The API key is read from the environment; downloads stay under ignored `data/`.
Google's mesh is a surface model: it includes trees and buildings.
"""
import argparse
import json
import os
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.request import urlopen
import numpy as np
from rasterio.warp import transform

ROOT = 'https://tile.googleapis.com/v1/3dtiles/root.json'


def box_reaches(box, centre, radius):
    """True when an oriented 3D Tiles box comes within `radius` of `centre`."""
    offset = centre - np.array(box[:3]); axes = np.array(box[3:]).reshape(3, 3); lengths = np.linalg.norm(axes, axis=1) + 1e-9
    beyond = np.clip(np.abs(axes @ offset) / lengths - lengths, 0, None)
    return np.hypot.reduce(beyond) <= radius


def collect_tiles(key, centre, radius, max_error_m, log=None):
    """Finest available tiles near `centre` as (url, geometric error, box centre), stopping once error is small enough."""
    session = {}; found = []; requests = [0]

    def fetch(url, attempts=4):
        query = '&'.join(f'{k}={v}' for k, v in {'key': key, **session}.items())
        for attempt in range(attempts):
            try:
                requests[0] += 1
                if log and requests[0] % 100 == 0: log(f'{requests[0]} requests, {len(found)} tiles')
                return urlopen(url + ('&' if '?' in url else '?') + query, timeout=30).read()
            except OSError:
                if attempt == attempts - 1: raise
                time.sleep(2 * (attempt + 1))

    def walk(node, base, pending):
        if not box_reaches(node['boundingVolume']['box'], centre, radius): return
        uri = (node.get('content') or {}).get('uri')
        if uri and uri.split('?')[0].endswith('.json'):
            url = urljoin(base, uri); extra = parse_qs(urlparse(url).query)
            if 'session' in extra: session['session'] = extra['session'][0]
            pending.append(url); return
        if node.get('children') and node['geometricError'] > max_error_m:
            for child in node['children']: walk(child, base, pending)  # children elsewhere do not make this coarse tile a leaf
        elif uri:
            found.append((urljoin(base, uri).split('?')[0], node['geometricError'], node['boundingVolume']['box'][:3]))

    def expand(url):
        pending = []; walk(json.loads(fetch(url.split('?')[0]))['root'], url, pending); return pending

    frontier = [ROOT]
    with ThreadPoolExecutor(12) as pool:
        while frontier: frontier = [url for batch in pool.map(expand, frontier) for url in batch]
    return found, fetch


def glb_points(data):
    """Vertex positions (ECEF metres, float64) and triangles from one Draco-compressed GLB tile."""
    import DracoPy
    length = struct.unpack('<I', data[12:16])[0]; gltf = json.loads(data[20:20 + length]); binary = data[20 + length + 8:]
    points, faces, offset = [], [], 0

    def accessor(index):
        item = gltf['accessors'][index]; view = gltf['bufferViews'][item['bufferView']]
        kind = {5121: 'u1', 5123: '<u2', 5125: '<u4', 5126: '<f4'}[item['componentType']]; width = {'SCALAR': 1, 'VEC3': 3}[item['type']]
        start = view.get('byteOffset', 0) + item.get('byteOffset', 0); stride = view.get('byteStride') or np.dtype(kind).itemsize * width
        raw = np.frombuffer(binary, 'u1', stride * (item['count'] - 1) + np.dtype(kind).itemsize * width, start)
        rows = np.lib.stride_tricks.as_strided(raw, (item['count'], np.dtype(kind).itemsize * width), (stride, 1))
        return np.ascontiguousarray(rows).view(kind).reshape(item['count'], width)

    for node in gltf['nodes']:
        if 'mesh' not in node: continue
        matrix = np.array(node['matrix'], float).reshape(4, 4).T if 'matrix' in node else np.eye(4)
        if 'translation' in node: matrix[:3, 3] = node['translation']
        for primitive in gltf['meshes'][node['mesh']]['primitives']:
            draco = primitive.get('extensions', {}).get('KHR_draco_mesh_compression')
            if draco:
                view = gltf['bufferViews'][draco['bufferView']]
                mesh = DracoPy.decode(binary[view.get('byteOffset', 0):view.get('byteOffset', 0) + view['byteLength']])
                local = np.asarray(mesh.points, float).reshape(-1, 3); triangles = np.asarray(mesh.faces).reshape(-1, 3)
            else:
                local = accessor(primitive['attributes']['POSITION']).astype(float); triangles = accessor(primitive['indices']).reshape(-1, 3).astype(int)
            world = local @ matrix[:3, :3].T + matrix[:3, 3]
            # glTF is y-up; 3D Tiles content is z-up ECEF.
            points.append(np.column_stack([world[:, 0], -world[:, 2], world[:, 1]]))
            faces.append(triangles + offset); offset += len(local)
    return np.concatenate(points), np.concatenate(faces)


def surface_grid(package, output, spacing_m=2.5, max_error_m=2.5):
    """Download tiles for the package's patch square and write `google-surface.npy` on a `spacing_m` grid."""
    key = os.environ.get('GOOGLE_MAPS_API_KEY') or os.environ['NEXT_PUBLIC_GOOGLE_MAPS_TOKEN']
    m = json.loads((Path(package) / 'manifest.json').read_text()); cx, cy = m['origin_utm_m']; half = m['size_m'] / 2
    centre = np.array([v[0] for v in transform(m['source_crs'], 'EPSG:4978', [cx], [cy], [m['base_elevation_m']])])
    log = lambda text: print(text, file=sys.stderr, flush=True)
    tiles, fetch = collect_tiles(key, centre, half * 1.45, max_error_m, log)
    log(f'{len(tiles)} tiles in range')
    # The walk covers a sphere; keep the tiles whose centres fall in the square plus a margin.
    ex, ey, _ = transform('EPSG:4978', m['source_crs'], *np.array([t[2] for t in tiles]).T)
    tiles = [t for t, x, y in zip(tiles, ex, ey) if abs(x - cx) < half + 80 and abs(y - cy) < half + 80]
    cache = Path(output) / 'google-tiles'; cache.mkdir(parents=True, exist_ok=True)

    def cached(tile):
        path = cache / (tile[0].rsplit('/', 1)[1].replace('.glb', '')[-60:] + '.glb')
        if not path.exists(): path.write_bytes(fetch(tile[0]))
        return path.read_bytes()

    with ThreadPoolExecutor(16) as pool: blobs = list(pool.map(cached, tiles))
    log(f'{len(tiles)} tiles downloaded')
    count = int(round(2 * half / spacing_m)) + 1; grid = np.full((count, count), -np.inf, 'float32')
    for blob in blobs:
        ecef, faces = glb_points(blob)
        x, y, h = (np.asarray(v) for v in transform('EPSG:4978', m['source_crs'], ecef[:, 0], ecef[:, 1], ecef[:, 2]))
        # Sample each triangle densely enough to fill the grid, keeping the highest surface per cell.
        a, b, c = (np.column_stack([x, y, h])[faces[:, i]] for i in range(3))
        size = np.maximum(np.linalg.norm(b - a, axis=1), np.linalg.norm(c - a, axis=1))
        for steps in np.unique(np.clip(np.ceil(size / spacing_m * 1.5), 1, 40).astype(int)):
            pick = np.clip(np.ceil(size / spacing_m * 1.5), 1, 40).astype(int) == steps
            u, v = np.meshgrid(np.arange(steps + 1), np.arange(steps + 1)); keep = u + v <= steps
            u, v = u[keep] / steps, v[keep] / steps
            pts = (a[pick, None] * (1 - u - v)[None, :, None] + b[pick, None] * u[None, :, None] + c[pick, None] * v[None, :, None]).reshape(-1, 3)
            col = np.rint((pts[:, 0] - (cx - half)) / spacing_m).astype(int); row = np.rint(((cy + half) - pts[:, 1]) / spacing_m).astype(int)
            ok = (col >= 0) & (col < count) & (row >= 0) & (row < count)
            np.maximum.at(grid, (row[ok], col[ok]), pts[ok, 2].astype('float32'))
    output = Path(output); output.mkdir(parents=True, exist_ok=True); np.save(output / 'google-surface.npy', grid)
    (output / 'google-surface.json').write_text(json.dumps({'service': 'Google Map Tiles API, Photorealistic 3D Tiles', 'tiles': len(tiles),
        'geometric_error_m': sorted({round(t[1], 2) for t in tiles}), 'spacing_m': spacing_m, 'height': 'metres above WGS84 ellipsoid; surface model including trees',
        'empty_cells': int(np.isinf(grid).sum()), 'note': 'Local working copy under Google Maps Platform terms; do not redistribute.'}, indent=2) + '\n')
    return grid


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package', type=Path, default=Path('data/style-patch'))
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    grid = surface_grid(args.package, args.output); print(grid.shape, int(np.isinf(grid).sum()), 'empty cells')
