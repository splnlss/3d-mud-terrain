"""Portable patch boundaries: world axes, source validity and transactional publication."""
import json
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin


def raster(path, missing=False):
    h=np.array([[30,31,32,33,34],[20,21,22,23,24],[10,11,12,13,14],
                [0,1,2,3,4],[-10,-9,-8,-7,-6]],dtype='float32')
    if missing: h[2,2]=-9999
    with rasterio.open(path,'w',driver='GTiff',width=5,height=5,count=1,
                       dtype='float32',crs='EPSG:32613',transform=from_origin(95,205,10,10),nodata=-9999) as dst:
        dst.write(h,1)


def test_patch_preserves_north_east_and_global_origin(tmp_path):
    from bake.style.patch import read_patch
    path=tmp_path/'dem.tif';raster(path)
    h,m=read_patch(path,(120,180),20)
    np.testing.assert_array_equal(h,[[21,22,23],[11,12,13],[1,2,3]])
    assert m['origin_utm_m']==[120,180]
    assert m['spacing_m']==10
    assert m['bounds_m']==[-10,-10,10,10]
    assert m['sample_origin_utm_m']==[110,190]


def test_patch_rejects_missing_coverage(tmp_path):
    from bake.style.patch import read_patch
    path=tmp_path/'dem.tif';raster(path,missing=True)
    with pytest.raises(ValueError,match='missing'):read_patch(path,(120,180),20)
    with pytest.raises(ValueError,match='coverage'):read_patch(path,(90,180),40)


def test_manifest_rejects_escape_paths(tmp_path):
    from bake.style.package import write_package
    with pytest.raises(ValueError,match='relative|escape'):
        write_package(tmp_path,{'schema_version':1,'files':['../secret']})
    with pytest.raises(ValueError,match='missing'):
        write_package(tmp_path,{'schema_version':1,'files':['meshes/absent.glb']})
    assert not (tmp_path/'manifest.json').exists()


def test_failed_bake_preserves_previous_package(tmp_path):
    from bake.style.package import package_stage,write_package
    out=tmp_path/'package'
    with package_stage(out) as stage:
        (stage/'source').mkdir();(stage/'source/a.txt').write_text('original')
        write_package(stage,{'schema_version':1,'files':['source/a.txt']})
    before={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
    with pytest.raises(RuntimeError):
        with package_stage(out) as stage:
            (stage/'partial').write_text('new');raise RuntimeError('bake failed')
    assert before=={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
