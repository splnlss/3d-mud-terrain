"""Window real elevation without resampling its source grid."""
import hashlib
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window


def read_patch(dem_path: Path, center_utm: tuple[float,float], size_m: float):
    with rasterio.open(dem_path) as src:
        spacing=src.res[0]
        if (src.crs is None or not src.crs.is_projected or abs(src.res[1]-spacing)>1e-6
                or src.transform.b or src.transform.d or src.transform.e>=0):
            raise ValueError('patch requires north-up square projected source pixels')
        cells=round(size_m/spacing)
        if size_m<=0 or cells%2 or abs(cells*spacing-size_m)>1e-5:
            raise ValueError('patch size must be an even multiple of source spacing')
        row,col=src.index(*center_utm)
        start_row,start_col=row-cells//2,col-cells//2
        if min(start_row,start_col)<0 or start_row+cells>=src.height or start_col+cells>=src.width:
            raise ValueError('DEM coverage does not enclose the requested patch')
        data=src.read(1,window=Window(start_col,start_row,cells+1,cells+1),masked=True)
        if np.ma.getmaskarray(data).any() or not np.isfinite(data.data).all():
            raise ValueError('patch contains missing elevation samples')
        x,north=src.xy(start_row,start_col)
        cx,cy=src.xy(row,col)
        half=size_m/2
        metadata={'source_crs':str(src.crs),'origin_utm_m':[cx,cy],
                  'requested_origin_utm_m':list(center_utm),'spacing_m':spacing,
                  'sample_origin_utm_m':[x,north],'bounds_m':[-half,-half,half,half],
                  'size_m':size_m,'samples':list(data.shape)}
        return np.asarray(data,dtype='float32'),metadata


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
