"""Sculpt fields must be stable when the same world surface is tiled."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree


def test_world_crop_and_repeatability():
    from bake.style.surface import sculpt_field
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    east,north=np.meshgrid(np.linspace(1000,1800,81),np.linspace(2400,1600,81))
    source=2600+.15*east+.2*north
    full=sculpt_field(east,north,source,recipe)
    again=sculpt_field(east,north,source,recipe)
    crop=sculpt_field(east[10:60,10:60],north[10:60,10:60],source[10:60,10:60],recipe)
    np.testing.assert_array_equal(full['height'],again['height'])
    np.testing.assert_allclose(full['height'][12:58,12:58],crop['height'][2:-2,2:-2],atol=1e-5)
    assert full['clast_instances']==again['clast_instances']
    assert full['clast_instances']
    for c in full['clast_instances']:
        assert 4<=c['radii_m'][0]<=20
        assert .2<=c['radii_m'][1]/c['radii_m'][0]<=.6


def test_cluster_spread_rejects_grid_and_preserves_gaps():
    from bake.style.surface import placement_spread,cluster_layout
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    x,y=np.meshgrid(np.arange(10)*10,np.arange(10)*10)
    assert placement_spread(np.c_[x.ravel(),y.ravel()])<.01
    instances,stats=cluster_layout((-1000,-1000,1000,1000),recipe)
    points=np.array([c['position_m'][::2] for c in instances])
    assert placement_spread(points)>.3
    assert .35<=stats['inside_occupancy']<=.65
    assert stats['outside_occupancy']<.1


def test_clasts_follow_sloped_surface_instead_of_being_buried_flat():
    from bake.style.surface import sculpt_field
    from scipy.spatial.transform import Rotation
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    recipe['fold_amplitude_m']=0
    x,north=np.meshgrid(np.linspace(-500,500,101),np.linspace(500,-500,101))
    field=sculpt_field(x,north,2700+.3*x,recipe)
    expected=np.array([-.3*recipe['height_gain'],1,0]);expected/=np.linalg.norm(expected)
    for c in field['clast_instances']:
        up=Rotation.from_quat(c['orientation_xyzw']).apply([0,1,0])
        np.testing.assert_allclose(up,expected,atol=1e-5)
