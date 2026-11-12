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
    # The directional-wear filter requires an 80 m halo. Published cells crop
    # from one globally authored patch; only compare the valid interior here.
    np.testing.assert_allclose(full['height'][18:52,18:52],crop['height'][8:-8,8:-8],atol=1e-5)
    assert full['clast_instances']==again['clast_instances']
    assert full['clast_instances']
    for c in full['clast_instances']:
        assert (1.3<=c['radii_m'][0]<=3.5) if c.get('band')=='crust' else (2<=c['radii_m'][0]<=8)
        ratio=c['radii_m'][1]/c['radii_m'][0]
        assert (.6<=ratio<=.9) if c.get('band')=='crust' else (.2<=ratio<=.6)


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
    recipe['clay_stamps']=False;recipe['surface_grain']=None;recipe['striation']=None;recipe['aggregate_relief_m']=0 # analytic planar receiver, with all sculpt displacement disabled
    x,north=np.meshgrid(np.linspace(-500,500,101),np.linspace(500,-500,101))
    field=sculpt_field(x,north,2700+.3*x,recipe)
    expected=np.array([-.3*recipe['height_gain'],1,0]);expected/=np.linalg.norm(expected)
    for c in field['clast_instances']:
        up=Rotation.from_quat(c['orientation_xyzw']).apply([0,1,0])
        np.testing.assert_allclose(up,expected,atol=1e-5)


def test_convex_clay_tops_stay_exposed_and_concavities_collect_aggregate():
    from bake.style.surface import sculpt_field
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    recipe['fold_amplitude_m']=0;recipe['clay_stamps']=False;recipe['surface_grain']=None;recipe['striation']=None;recipe['aggregate_relief_m']=0
    x,y=np.meshgrid(np.linspace(-50,50,21),np.linspace(50,-50,21))
    peak=sculpt_field(x,y,2700-.02*(x*x+y*y),recipe)
    bowl=sculpt_field(x,y,2700+.02*(x*x+y*y),recipe)
    assert peak['crust'][10,10]>bowl['crust'][10,10]
    assert bowl['cavity'][10,10]>peak['cavity'][10,10]


def test_fine_crust_geometry_collects_on_steep_faces_not_flat_dust():
    from bake.style.surface import sculpt_field
    recipe=json.loads(Path('configs/style-materials.json').read_text())
    recipe['fold_amplitude_m']=0;recipe['clay_stamps']=False;recipe['surface_grain']=None;recipe['striation']=None;recipe['aggregate_relief_m']=0
    recipe['clusters']['probability']=0
    x,y=np.meshgrid(np.linspace(-100,100,41),np.linspace(100,-100,41))
    flat=sculpt_field(x,y,np.full(x.shape,2700.),recipe)
    steep=sculpt_field(x,y,2700+.7*x,recipe)
    assert not [c for c in flat['clast_instances'] if c.get('band')=='crust']
    assert len([c for c in steep['clast_instances'] if c.get('band')=='crust'])>100
