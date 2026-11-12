"""Matched LOD fixtures retain contact constraints and account for removed relief."""
import json
import numpy as np
from tests.test_tile import unpack_glb,attribute


def test_residual_full_detail_is_neutral_and_coarse_receiver_recovers_slope():
    from bake.style.lod import residual_normal
    x,y=np.meshgrid(np.arange(17),np.arange(17))
    master=.2*x+.4*y
    full=residual_normal(master,master,1)
    np.testing.assert_allclose(full,np.broadcast_to([0,0,1],full.shape),atol=1/255)
    coarse=residual_normal(master,np.zeros_like(master),1)
    expected=np.array([-.2,.4,1]);expected/=np.linalg.norm(expected)
    np.testing.assert_allclose(coarse[2:-2,2:-2],np.broadcast_to(expected,coarse[2:-2,2:-2].shape),atol=.001)


def test_lod_protects_shore_edges_and_reports_actual_error(tmp_path):
    from bake.style.lod import derive_lods
    x,y=np.meshgrid(np.linspace(-32,32,33),np.linspace(32,-32,33))
    height=5*np.exp(-(x*x+y*y)/90)+.03*x
    protected=np.zeros(height.shape,bool);protected[:,16]=True
    source=tmp_path/'fixture.npz';np.savez(source,height=height,protected=protected)
    levels=derive_lods(source,{'bounds_m':[-32,-32,32,32]},tmp_path/'lod')
    assert len(levels)==3
    for level in levels:
        doc,binary=unpack_glb(tmp_path/'lod'/level['path'])
        pos=attribute(doc,binary,doc['meshes'][0]['primitives'][0]['attributes']['POSITION'])
        for row in [0,32]:
            for col in range(33):assert np.any(np.all(np.isclose(pos,[x[row,col],height[row,col],-y[row,col]],atol=1e-5),axis=1))
        for row in range(33):assert np.any(np.all(np.isclose(pos,[0,height[row,16],-y[row,16]],atol=1e-5),axis=1))
        reconstructed=np.load(tmp_path/'lod'/level['receiver'])
        assert np.max(abs(height-reconstructed))<=level['geometric_error_m']+1e-5
    assert levels[0]['geometric_error_m']<1e-4
    assert levels[-1]['geometric_error_m']>0
