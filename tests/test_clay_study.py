import numpy as np
from bake.style.clay_study import author_study


def test_clay_study_is_continuous_embedded_relief_with_smooth_and_crusted_areas():
    maps = author_study(resolution=256)
    assert np.array_equal(maps['height'],author_study(resolution=256)['height'])
    assert np.isfinite(maps['height']).all()
    assert .08 < np.ptp(maps['height']) < .3
    assert np.all(maps['aggregate_height'] >= 0)
    assert np.max(maps['aggregate_height']) < .018
    assert .1 < np.mean(maps['crust']>.3) < .7
    assert np.mean(maps['crust']<.05) > .15
    assert .4 < maps['roughness'].min() < .65
    assert maps['roughness'].max() > .8
    assert np.allclose(np.linalg.norm(maps['normal'],axis=-1),1,atol=1e-5)
