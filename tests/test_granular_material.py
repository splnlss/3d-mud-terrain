import numpy as np
from bake.style.granular import author_granular


def test_granular_maps_share_physical_relief_and_variable_finish():
    maps = author_granular(resolution=128, span_m=16, seed=91)
    again = author_granular(resolution=128, span_m=16, seed=91)
    assert np.array_equal(maps['height'], again['height'])
    assert np.isfinite(maps['height']).all()
    assert np.ptp(maps['height']) > .2
    assert np.allclose(np.linalg.norm(maps['normal'],axis=-1), 1, atol=1e-5)
    assert .28 <= maps['roughness'].min() < .6
    assert .8 < maps['roughness'].max() <= .96
    assert np.std(maps['roughness']) > .08
    # Periodic central derivatives, including both edges, define the normals.
    height = maps['height']; spacing = 16/128
    east = (np.roll(height,-1,1)-np.roll(height,1,1))/(2*spacing)
    south = (np.roll(height,-1,0)-np.roll(height,1,0))/(2*spacing)
    expected = np.stack([-east,south,np.ones_like(height)],axis=-1)
    expected /= np.linalg.norm(expected,axis=-1,keepdims=True)
    assert np.allclose(expected,maps['normal'],atol=1e-5)
