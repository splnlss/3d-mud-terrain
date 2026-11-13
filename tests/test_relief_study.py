import numpy as np
from bake.style.relief_study import author_specimen


def test_relief_specimen_is_deterministic_with_flat_channel_bare_faces_and_raised_crust():
    maps = author_specimen(resolution=320)
    assert np.array_equal(maps['height'], author_specimen(resolution=320)['height'])
    assert np.isfinite(maps['height']).all() and np.isfinite(maps['base_color']).all()
    assert .06 < np.ptp(maps['height']) < .25
    channel = maps['channel'] > .99
    assert .03 < channel.mean() < .3
    assert np.ptp(maps['height'][channel]) < .003
    crusted = maps['crust'] > .5
    assert .08 < crusted.mean() < .6
    assert (maps['crust'] < .05).mean() > .25
    assert np.all(maps['nodules'] >= 0) and maps['nodules'][channel].max() < 1e-4
    # Crust is darker and rougher than the bare clay it sits in.
    land = ~channel & (maps['crust'] < .05)
    covered = maps['nodules'] > .001
    assert maps['base_color'][covered].mean() < maps['base_color'][land].mean()
    assert maps['roughness'][covered].mean() > maps['roughness'][land].mean() + .1


def test_drainage_accumulates_downhill_into_the_valley_line():
    from bake.style.relief_patch import drainage
    rows, cols = np.mgrid[0:21, 0:21]
    # A V-shaped valley along column 10, falling toward row 20.
    down, area = drainage((np.abs(cols - 10) * 2.0 + (20 - rows) * .5).astype('float32'))
    assert area[6:20, 10].min() > area[:, 5].max()
    assert np.all(np.diff(area[2:20, 10]) > 0)
    assert down[10 * 21 + 5] in (10 * 21 + 6, 11 * 21 + 6)


def test_field_parcels_find_a_striped_rectangle_and_a_centre_pivot():
    from bake.style.fields import field_parcels
    rows, cols = np.mgrid[0:400, 0:400]
    cir = np.zeros((400, 400, 3)) + [90, 120, 110]  # dry ground: low near-infrared
    square = (rows > 40) & (rows < 180) & (cols > 40) & (cols < 200)
    disc = np.hypot(rows - 290, cols - 280) < 75
    cir[square | disc] = [200, 60, 80]
    cir[square, 0] += 6 * np.sin(cols[square] / 2.0)  # rows running north-south
    ids, parcels = field_parcels(cir, 2000)
    assert len(parcels) == 2 and sorted(p['pivot'] for p in parcels) == [False, True]
    field = next(p for p in parcels if not p['pivot'])
    assert abs(np.cos(field['row_normal_rad'])) > .95
    assert ids[110, 120] != ids[290, 280] and ids[5, 5] == 0
