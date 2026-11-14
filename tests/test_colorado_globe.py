import numpy as np
from bake.style.colorado_globe import project, cap_positions, coverage_radius, border_crossings


def test_colorado_and_200_mile_corner_buffers_fit_above_ground():
    x, y = project(np.array([-109.06, -102.04, -109.06, -102.04]), np.array([37, 37, 41, 41]))
    radius = coverage_radius()
    assert radius >= np.hypot(x, y).max() + 321868.8
    p = cap_positions(np.array([-.18*radius, radius]), np.array([.10*radius, 0.]), np.zeros(2))
    assert p[0, 2] > .3
    assert abs(p[1, 2]) < 1e-6


def test_east_is_right_north_is_back_and_heights_are_radial():
    x, y = project(np.array([-106, -105]), np.array([39, 39]))
    assert x[1] > x[0]
    p = cap_positions(np.array([0., 1000.]), np.array([0., 1000.]), np.zeros(2))
    assert p[1, 0] > p[0, 0] and p[1, 1] > p[0, 1]
    lifted = cap_positions(np.array([0., 1000.]), np.array([0., 1000.]), np.full(2, .1))
    assert np.allclose(np.linalg.norm(lifted-p, axis=1), .1)
    assert np.all(lifted[:,2] > p[:,2])


def test_crossings_interpolate_on_actual_segments_without_relocating():
    a = border_crossings([[-105.72, 37.1], [-105.68, 36.9]], axis=1, value=37)
    assert np.allclose(a, [[-105.7, 37]])
    b = border_crossings([[-102.2, 38.03], [-101.9, 38.02]], axis=0, value=-102.05)
    assert np.allclose(b, [[-102.05, 38.025]])


def test_isolated_summit_is_rounded_without_shifting_range():
    from bake.style.colorado_globe import sculpt_elevation, GAIN, DATUM_M
    height = np.full((101,101), 1800.)
    height[50,50] = 4300
    shaped = sculpt_elevation(height, 1.)
    baseline = (1800 - DATUM_M) * GAIN
    assert np.unravel_index(shaped.argmax(), shaped.shape) == (50,50)
    assert shaped.max() - baseline < 2000  # A raw DEM spike at this gain would be 250,000.
    assert abs(shaped[50,49] - shaped[50,50]) < 100
    assert np.allclose(shaped, shaped[::-1,::-1])


def test_state_spans_crown_with_plains_wrapped_to_right_shoulder():
    from bake.style.colorado_globe import display_map, SPAN
    x, y = project(np.array([-109.05, -105.2, -102.05, -107.6]), np.array([39., 39.3, 39., 37.7]))
    p = cap_positions(x, y, np.zeros(4)); half = SPAN / 2
    west, front, east, sanjuan = p[:, 0] / half
    assert east - west >= .72 * 2            # state covers most of the cap width
    assert east >= .83 and west <= -.58      # both boundaries approach the shoulders
    assert .3 < front < .6 and sanjuan < 0   # Front Range right of centre, San Juans left
    assert east - front < front - west       # plains compressed relative to the mountain side
    angle = np.linspace(0, 2*np.pi, 200); radius = coverage_radius()
    bx, by = display_map(radius*np.cos(angle), radius*np.sin(angle))
    assert np.allclose(np.hypot(bx, by), radius)


def test_rim_taper_follows_display_radius_not_source_radius():
    from bake.style.colorado_globe import rim_taper
    radius = coverage_radius()
    assert rim_taper(np.array([0.]), np.array([0.]))[0] == 1
    assert rim_taper(np.array([.86*radius]), np.array([0.]))[0] < .5   # display radius is about .98 R after compression
    assert rim_taper(np.array([radius]), np.array([0.]))[0] == 0


def test_relief_is_full_in_the_state_and_reduced_in_the_compressed_buffer():
    from bake.style.colorado_globe import relief_scale
    radius = coverage_radius(); x, y = np.meshgrid(np.linspace(-radius, radius, 201), np.linspace(radius, -radius, 201))
    scale = relief_scale(x, y); sx, sy = project(np.array([-105.5]), np.array([39.]))
    row, col = int(round((radius - sy[0]) / (2 * radius) * 200)), int(round((sx[0] + radius) / (2 * radius) * 200))
    assert scale[row, col] == 1 and scale[100, 190] < .5 and scale.min() >= 0


def test_narrow_diagonal_channel_mask_is_continuous_and_two_cells_wide():
    from bake.style.colorado_globe import channel_distance_m
    from shapely.geometry import LineString
    n, radius = 129, 64_000.           # 1 km cells
    bank = channel_distance_m([(LineString([(-60_000, -60_000), (60_000, 60_000)]), 900)], n, radius)
    inside = bank < 0
    assert inside.sum() >= 2 * 120 * .9     # about two cells across every diagonal row
    rows = np.nonzero(inside.any(axis=1))[0]
    assert np.array_equal(rows, np.arange(rows[0], rows[-1] + 1))   # no gaps along the course
    assert abs(bank.min() + 900) < 600 and bank.max() > 50_000


def test_channel_bed_sits_below_valley_banks():
    from bake.style.colorado_globe import channel_level
    n = 101; rows = np.arange(n)[:, None]; height = np.abs(rows - 50) * .002 + .05 + np.zeros((n, n))   # V valley, floor at row 50
    bank = np.abs(rows - 50) * 1000. - 900 + np.zeros((n, n))
    level = channel_level(height, bank, 1000.)
    assert np.allclose(level[50], .05, atol=1e-3)
    assert np.all(level[50] <= height[49] + 1e-6)


def test_display_warp_has_no_foldovers_or_reordered_east_west_locations():
    from bake.style.colorado_globe import display_map
    radius=coverage_radius()
    x,y=np.meshgrid(np.linspace(-.7,.7,61)*radius,np.linspace(-.7,.7,61)*radius)
    wx,wy=display_map(x,y)
    dx_x,dx_y=np.gradient(wx);dy_x,dy_y=np.gradient(wy)
    assert np.all(dx_y*dy_x-dx_x*dy_y>0)
    assert np.all(np.diff(wx,axis=1)>0)
