"""Analytic normal sign and coherent physical material maps."""
import numpy as np


def test_neutral_and_north_rising_normal_convention():
    from bake.style.maps import normal_from_height
    flat=np.zeros((9,9))
    n=normal_from_height(flat,1)
    np.testing.assert_allclose(n,np.broadcast_to([0,0,1],n.shape),atol=1e-6)
    ramp=np.tile(np.arange(8,-1,-1)[:,None],(1,9))
    n=normal_from_height(ramp,1)
    np.testing.assert_allclose(n[4,4],[0,-2**-.5,2**-.5],atol=1e-6)
    assert normal_from_height(-ramp,1)[4,4,1]>0


def test_material_maps_are_finite_coregistered_and_nonuniform():
    from bake.style.maps import author_material
    maps=author_material({'seed':4271,'kind':'granular','span_m':128},128)
    for field in maps.values():
        assert field.shape[:2]==(128,128)
        assert np.isfinite(field).all()
    np.testing.assert_allclose(np.linalg.norm(maps['normal'],axis=-1),1,atol=1e-5)
    assert np.ptp(maps['height'])>1
    assert np.ptp(maps['roughness'])>.05


def test_failed_authoring_keeps_existing_source_masters(tmp_path):
    from bake.style.author import author
    import json
    from pathlib import Path
    import pytest
    package=tmp_path/'package';(package/'source').mkdir(parents=True)
    (package/'.terrain-style-package').write_text('terrain-style-v1\n')
    np.save(package/'source/dem.npy',np.ones((9,9),dtype='float32')*2700)
    (package/'source/sculpted.npz').write_bytes(b'previous master')
    (package/'manifest.json').write_text(json.dumps({'schema_version':1,'size_m':80,'base_elevation_m':2700,'files':['source/dem.npy','source/sculpted.npz']}))
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    recipe['materials']=[{'kind':'clay'}] # missing physical span fails after sculpting
    path=tmp_path/'bad.json';path.write_text(json.dumps(recipe))
    with pytest.raises(KeyError):author(package,path)
    assert (package/'source/sculpted.npz').read_bytes()==b'previous master'
