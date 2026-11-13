"""Public Sentinel-2 reflectance and classification, cached in the terrain frame."""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling, transform_bounds

from bake.dem import CRS

STAC = 'https://earth-search.aws.element84.com/v1/search'


def fetch_imagery(manifest, spacing=40):
    size = manifest['size_m']
    cache = Path(f'data/sentinel-{size}-{spacing}.npz')
    metadata_path = cache.with_suffix('.json')
    if cache.exists() and metadata_path.exists():
        arrays = np.load(cache)
        return dict(arrays), json.loads(metadata_path.read_text())
    cx, cy = manifest['center_utm_m']
    half = size/2
    bounds = (cx-half, cy-half, cx+half, cy+half)
    bbox = transform_bounds(CRS, 'EPSG:4326', *bounds, densify_pts=21)
    search_path = Path(f'data/sentinel-search-{size}.json')
    if search_path.exists():
        search = json.loads(search_path.read_text())
    else:
        payload = {'collections': ['sentinel-2-l2a'], 'bbox': list(bbox),
                   'datetime': '2026-07-01T00:00:00Z/2026-08-31T23:59:59Z',
                   'limit': 100, 'query': {'eo:cloud_cover': {'lt': 5}}}
        with urlopen(Request(STAC, data=json.dumps(payload).encode(),
                             headers={'Content-Type': 'application/json'}), timeout=60) as response:
            search = json.load(response)
        search_path.write_text(json.dumps(search))
    # One lowest-cloud acquisition per MGRS cell; sort for deterministic overlaps.
    chosen = {}
    for feature in search['features']:
        cell = feature['id'].split('_')[1]
        if cell not in chosen or feature['properties']['eo:cloud_cover'] < chosen[cell]['properties']['eo:cloud_cover']:
            chosen[cell] = feature
    if not chosen:
        raise ValueError('no clear Sentinel-2 imagery found for the requested extent')
    count = int(size/spacing)+1
    grid = from_origin(cx-half-spacing/2, cy+half+spacing/2, spacing, spacing)
    bands = {name: np.zeros((count, count), dtype='float32') for name in ['green', 'nir', 'red']}
    scl = np.zeros((count, count), dtype='uint8')
    sources = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_TIMEOUT='90'):
        for cell, feature in sorted(chosen.items()):
            print(f'  Reading Sentinel-2 {feature["id"]}…', flush=True)
            read = {}
            for name in ['green', 'nir', 'red', 'scl']:
                asset = feature['assets'][name]
                with rasterio.open(asset['href']) as src:
                    with WarpedVRT(src, crs=CRS, transform=grid, width=count, height=count,
                                   resampling=Resampling.nearest if name=='scl' else Resampling.bilinear,
                                   nodata=0) as vrt:
                        image = vrt.read(1)
                if name != 'scl':
                    band = asset.get('raster:bands', [{}])[0]
                    image = image.astype('float32')*band.get('scale', .0001)+band.get('offset', 0)
                read[name] = image
            valid = np.isin(read['scl'], [4, 5, 6, 7])
            for name in bands:
                bands[name][valid] = read[name][valid]
            scl[valid] = read['scl'][valid]
            sources.append({'id': feature['id'], 'date': feature['properties']['datetime'],
                            'cloud_percent': feature['properties']['eo:cloud_cover'],
                            'assets': {name: feature['assets'][name]['href'] for name in read}})
    valid = scl>0
    ndwi = np.where(valid, (bands['green']-bands['nir'])/np.maximum(bands['green']+bands['nir'], 1e-6), -1)
    ndvi = np.where(valid, (bands['nir']-bands['red'])/np.maximum(bands['nir']+bands['red'], 1e-6), 0)
    arrays = {'ndwi': ndwi.astype('float32'), 'ndvi': ndvi.astype('float32'), 'scl': scl}
    np.savez_compressed(cache, **arrays)
    metadata = {'catalog': STAC, 'sources': sources, 'spacing_m': spacing,
                'valid_coverage_fraction': float(valid.mean()),
                'terms': 'https://dataspace.copernicus.eu/explore-data/data-collections/sentinel-data/sentinel-2'}
    metadata_path.write_text(json.dumps(metadata, indent=2)+'\n')
    return arrays, metadata


def fetch_hydrography(manifest):
    import hashlib
    import zipfile
    import shutil
    import fiona
    path = Path(f'data/nhd-{manifest["size_m"]}.json')
    if path.exists():
        result = json.loads(path.read_text())
        catalog = Path(f'data/nhd-products-{manifest["size_m"]}.json')
        if catalog.exists():
            products = {item['downloadURL']: item for item in json.loads(catalog.read_text()).get('items', [])}
            for source in result.get('sources', []):
                item = products.get(source['url'], {})
                source.update({'title': item.get('title'), 'publication_date': item.get('publicationDate'),
                               'metadata_url': item.get('metaUrl')})
        return result
    cx, cy = manifest['center_utm_m']
    half = manifest['size_m']/2
    bbox = transform_bounds(CRS, 'EPSG:4326', cx-half, cy-half, cx+half, cy+half)
    query = {'datasets': 'National Hydrography Dataset (NHD) Best Resolution',
             'bbox': ','.join(map(str, bbox)), 'max': 100, 'outputFormat': 'JSON'}
    catalog = Path(f'data/nhd-products-{manifest["size_m"]}.json')
    if catalog.exists():
        products = json.loads(catalog.read_text())
    else:
        with urlopen('https://tnmaccess.nationalmap.gov/api/v1/products?'+urlencode(query), timeout=60) as response:
            products = json.load(response)
        catalog.write_text(json.dumps(products))
    product_map = {item['downloadURL']:item for item in products.get('items', [])
                    if '/HU4/GPKG/' in item['downloadURL']}
    urls = sorted(product_map)
    if not urls:
        raise ValueError('USGS catalog returned no NHD watershed GeoPackages')
    result = {'service': 'USGS staged NHD Best Resolution watershed GeoPackages',
              'sources': [], 'layers': {'6': [], '12': []}}
    seen = set()
    for url in urls:
        archive = Path('data')/url.rsplit('/',1)[1]
        if not archive.exists():
            print(f'  Downloading {archive.name}…', flush=True)
            temporary = archive.with_suffix('.tmp.zip')
            with urlopen(url,timeout=90) as response,temporary.open('wb') as output:
                shutil.copyfileobj(response,output)
            temporary.replace(archive)
        with zipfile.ZipFile(archive) as bundle:
            names = [name for name in bundle.namelist() if name.endswith('.gpkg')]
            if len(names)!=1:
                raise ValueError('NHD archive must contain exactly one GeoPackage')
        # GDAL reads the compressed archive directly; do not expand it onto disk.
        gpkg = f'zip://{archive.resolve()}!{names[0]}'
        result['sources'].append({'url': url, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                                  'title': product_map[url].get('title'),
                                  'publication_date': product_map[url].get('publicationDate'),
                                  'metadata_url': product_map[url].get('metaUrl')})
        available = fiona.listlayers(gpkg)
        for number, suffix in [('6','NHDFlowline'), ('12','NHDWaterbody')]:
            layer = next(name for name in available if name.lower()==suffix.lower())
            with fiona.open(gpkg, layer=layer) as source:
                local_bbox = transform_bounds('EPSG:4326', source.crs, *bbox)
                for feature in source.filter(bbox=local_bbox):
                    props = {key.lower(): value for key,value in dict(feature.properties).items()}
                    key = (number, props.get('permanent_identifier'))
                    if key in seen:
                        continue
                    if number=='6' and (props.get('ftype') not in [460,336,558] or (props.get('ftype')==460 and props.get('fcode') not in [46000,46006])):
                        continue
                    if number=='12' and props.get('ftype') not in [390,436]:
                        continue
                    seen.add(key)
                    from rasterio.warp import transform_geom
                    geometry = transform_geom(source.crs, 'EPSG:4326', dict(feature.geometry))
                    result['layers'][number].append({'type': 'Feature', 'properties': props,
                                                     'geometry': geometry})
        print(f'  Read {archive.name}', flush=True)
    temporary = path.with_suffix('.tmp.json')
    temporary.write_text(json.dumps(result))
    temporary.replace(path)
    print('  NHD: '+', '.join(f'{k}: {len(v)} features' for k,v in result['layers'].items()), flush=True)
    return result


if __name__ == '__main__':
    manifest = json.loads(Path('data/san-luis-112640-10.json').read_text())
    _, metadata = fetch_imagery(manifest)
    print(f"Sentinel valid coverage: {metadata['valid_coverage_fraction']:.1%}")
    fetch_hydrography(manifest)
