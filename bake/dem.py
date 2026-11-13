"""Read the USGS 3DEP 1/3 arc-second DEM into a reproducible, local UTM grid."""
import hashlib
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import Resampling, transform
from rasterio.warp import transform_bounds
from rasterio.windows import Window

CRS = 'EPSG:32613'
CENTER_LON, CENTER_LAT = -105.42, 37.20
SOURCE_ROOT = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/13/TIFF/current'


def fetch_patch(size_m=12000, spacing_m=10, cache=Path('data')):
    """Cache only the reprojected patch; retain source identity with the raster."""
    if size_m <= 0 or spacing_m <= 0 or size_m % spacing_m:
        raise ValueError('size must be a positive multiple of spacing')
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    path = cache/f'san-luis-{size_m}-{spacing_m}.tif'
    manifest_path = path.with_suffix('.json')
    if path.exists() and manifest_path.exists():
        with rasterio.open(path) as src:
            return src.read(1), json.loads(manifest_path.read_text())
    cx, cy = transform('EPSG:4326', CRS, [CENTER_LON], [CENTER_LAT])
    half = size_m/2
    count = int(size_m/spacing_m)+1
    grid = from_origin(cx[0]-half-spacing_m/2, cy[0]+half+spacing_m/2,
                       spacing_m, spacing_m)
    geo_bounds = transform_bounds(CRS, 'EPSG:4326', cx[0]-half, cy[0]-half,
                                 cx[0]+half, cy[0]+half, densify_pts=21)
    heights = np.full((count, count), -999999, dtype='float32')
    sources = []
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',
                      CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif', GDAL_HTTP_TIMEOUT='90'):
        for lon in range(math.floor(geo_bounds[0]), math.ceil(geo_bounds[2])):
            for lat in range(math.floor(geo_bounds[1]), math.ceil(geo_bounds[3])):
                tile = f'n{lat+1:02d}w{abs(lon):03d}'
                source = f'{SOURCE_ROOT}/{tile}/USGS_13_{tile}.tif'
                print(f'  Reading USGS {tile}…', flush=True)
                # Record the revision of each mutable 'current' asset.
                with urlopen(Request(source, method='HEAD'), timeout=45) as response:
                    identity = {k: response.headers.get(k) for k in ['ETag', 'Last-Modified']}
                with rasterio.open(source) as src:
                    native = {'crs': str(src.crs), 'resolution': list(src.res)}
                    west, south, east, north = transform_bounds(src.crs, CRS, *src.bounds,
                                                               densify_pts=21)
                    col0 = max(0, math.floor((west-grid.c)/spacing_m))
                    col1 = min(count, math.ceil((east-grid.c)/spacing_m))
                    row0 = max(0, math.floor((grid.f-north)/spacing_m))
                    row1 = min(count, math.ceil((grid.f-south)/spacing_m))
                    with WarpedVRT(src, crs=CRS, transform=grid, width=count, height=count,
                                   resampling=Resampling.bilinear, nodata=-999999) as vrt:
                        patch = vrt.read(1, window=Window(col0, row0, col1-col0, row1-row0))
                    target = heights[row0:row1, col0:col1]
                    valid = patch > -500
                    target[valid] = patch[valid]
                    sources.append({'url': source, 'identity': identity, 'native': native})
    if not np.isfinite(heights).all() or heights.min() < -500:
        raise ValueError('USGS elevation patch contains missing data')
    temporary = path.with_suffix('.tmp.tif')
    with rasterio.open(temporary, 'w', driver='GTiff', height=count, width=count,
                       count=1, dtype='float32', crs=CRS, transform=grid,
                       compress='deflate') as dest:
        dest.write(heights, 1)
    temporary.replace(path)
    manifest = {
        'dataset': 'USGS 3DEP 1/3 arc-second (approximately 10 m)',
        'sources': sources,
        'source_terms': 'https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits',
        'center_wgs84': [CENTER_LON, CENTER_LAT], 'center_utm_m': [cx[0], cy[0]],
        'crs': CRS, 'size_m': size_m, 'spacing_m': spacing_m, 'samples': [count, count],
        'local_sample_bounds_m': [-half, -half, half, half],
        'elevation_range_m': [float(heights.min()), float(heights.max())],
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    return heights, manifest
