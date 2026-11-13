"""Material cues must follow landform shape and remain seamless."""
import numpy as np

from bake.material import material_fields, detail_textures


def test_crust_prefers_rounded_convex_tops_over_concave_pits():
    y, x = np.mgrid[-1:1:65j, -1:1:65j]
    hill = 3000-1000*(x*x+y*y)
    bowl = 1000+1000*(x*x+y*y)
    top = material_fields(hill.astype('float32'), 40)
    pit = material_fields(bowl.astype('float32'), 40)
    assert top.shape == (65, 65, 4)
    assert top[32, 32, 0] > pit[32, 32, 0]+.01
    assert top[32, 32, 2] > top[32, 0, 2]  # Dust prefers flat upward tops.
    assert pit[32, 32, 3] < top[32, 32, 3]  # Concavities carry darker AO.
    assert np.isfinite(top).all() and top.min()>=0 and top.max()<=1


def test_authored_detail_is_reproducible_with_valid_normals():
    a, b = detail_textures(32), detail_textures(32)
    assert set(a) == {'crust-albedo', 'crust-normal', 'granular-albedo', 'granular-normal'}
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])
        assert a[key].shape == (32, 32, 3)
    n = a['granular-normal'].astype('float32')/255*2-1
    assert np.max(np.abs(np.linalg.norm(n, axis=-1)-1))<.02


def test_miniature_flecks_and_strands_are_sparse_and_distinct_from_base_tone():
    atlas = detail_textures(512)['crust-albedo']
    assert 0 < (atlas[:,:,1]>0).mean() < .01
    assert 0 < (atlas[:,:,2]>0).mean() < .01


def test_crust_aspect_matches_the_runtime_sun_on_east_facing_slopes():
    x = np.linspace(-2560,2560,129)[None,:]
    west = np.repeat(1000+x*.2,129,axis=0).astype('float32')
    east = np.repeat(1000-x*.2,129,axis=0).astype('float32')
    assert material_fields(east,40)[64,64,0] > material_fields(west,40)[64,64,0]+.02


def test_crust_aspect_matches_the_southeast_sun_on_south_facing_slopes():
    south = np.linspace(-2560,2560,129)[:,None]
    north_facing = np.repeat(1000+south*.2,129,axis=1).astype('float32')
    south_facing = np.repeat(1000-south*.2,129,axis=1).astype('float32')
    assert material_fields(south_facing,40)[64,64,0] > material_fields(north_facing,40)[64,64,0]+.02


def test_small_clods_do_not_control_the_primary_material_split():
    axis=np.linspace(-1,1,129)
    y,x=np.meshgrid(axis,axis,indexing='ij')
    landform=(1000-200*(x*x+y*y)).astype('float32')
    clods=(60*np.sin(x*80)*np.cos(y*80)).astype('float32')
    baseline=material_fields(landform,40,landform=landform)
    noisy=material_fields(landform+clods,40,landform=landform)
    np.testing.assert_allclose(noisy[:,:,:3],baseline[:,:,:3])
    assert ((noisy[:,:,0]>.05)&(noisy[:,:,0]<.95)).mean()>.8


def test_default_light_is_on_the_camera_side_of_the_relief():
    from bake.material import SUN_DIRECTION
    eye=np.array([np.sin(.62),0,np.cos(.62)])
    assert np.dot(eye,SUN_DIRECTION)>0
