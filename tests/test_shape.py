"""The height curve must boost terraces without reversing mountain elevations."""
import numpy as np

from bake.shape import remap_height, clod_displacement, shape_dem


def test_curve_boosts_low_relief_and_compresses_high_relief_without_inversion():
    samples = np.array([2200, 2210, 2300, 2310, 4000, 4010], dtype='float32')
    result = remap_height(samples, base=2200, gain=5, knee=800)
    assert result[0] == 2200
    assert (np.diff(result)>0).all()
    assert result[1]-result[0]>40  # A 10 m terrace stays visible.
    assert result[-1]-result[-2]<20  # High peaks do not become spikes.


def test_clods_are_bounded_and_independent_of_tile_partition():
    x, y = np.meshgrid(np.arange(9)*10, np.arange(9)*10)
    whole = clod_displacement(x, y, amplitude=25)
    left = clod_displacement(x[:, :5], y[:, :5], amplitude=25)
    right = clod_displacement(x[:, 4:], y[:, 4:], amplitude=25)
    assert np.max(np.abs(whole))<=25
    np.testing.assert_allclose(whole[:, :5], left)
    np.testing.assert_allclose(left[:, -1], right[:, 0])


def test_outer_relief_falls_to_a_continuous_base_without_a_vertical_map_cut():
    result = shape_dem(np.full((17,17), 100, dtype='float32'), 160, 0,
                       amplitude=0, edge_width=40)
    assert (result[0]==0).all() and (result[-1]==0).all()
    assert (result[:,0]==0).all() and (result[:,-1]==0).all()
    assert result[8,8]>100
    assert 0 < result[1,8] < result[4,8]
