"""Image-matched relief specimen: pinched clay masses, crumb crust and a silt channel.

Target: docs/reference/style-studies/04-canyon.png (with 01/05 for landform spacing).
A labelled calibration specimen in model metres, not San Luis geometry. Every
height, colour and finish value derives from the same fields; colour holds no
baked light. `style_surface` takes any land base height plus a channel distance
field so the same recipe can later be driven by the real DEM and mapped water.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import splev, splprep
from scipy.ndimage import distance_transform_edt, gaussian_filter, map_coordinates, zoom
from scipy.spatial import cKDTree
from PIL import Image


def smoothstep(v, lo, hi):
    t = np.clip((v - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def hashed(ix, iy, salt):
    """Uniform values in (0, 1) fixed by integer position and salt, identical wherever a grid overlaps another."""
    h = (ix.astype('uint64') * np.uint64(0x9E3779B97F4A7C15)) ^ (iy.astype('uint64') * np.uint64(0xC2B2AE3D27D4EB4F)) ^ np.uint64(salt * 0x165667B19E3779F9 % 2 ** 64)
    for shift, mult in ((30, 0xBF58476D1CE4E5B9), (27, 0x94D049BB133111EB)):
        h = (h ^ (h >> np.uint64(shift))) * np.uint64(mult)
    return ((h ^ (h >> np.uint64(31))) >> np.uint64(11)).astype('float64') * (1.0 / 2 ** 53) + 1e-12


def hashed_normal(ix, iy, salt):
    return np.sqrt(-2 * np.log(hashed(ix, iy, salt))) * np.cos(2 * np.pi * hashed(ix, iy, salt + 7919))


class Fields:
    """Band-limited noise with zero mean and unit deviation, anchored to a global sample lattice.

    `origin` is the global (column, row) index of this grid's first sample. Two grids with the same
    seed and sample spacing produce identical values where they overlap, so neighbouring tiles agree.
    """

    def __init__(self, resolution, span, seed, origin=(0, 0)):
        self.n, self.span, self.px = resolution, span, span / (resolution - 1)
        self.seed, self.origin, self.calls = seed, origin, 0

    def salt(self):
        self.calls += 1
        return self.seed * 1000003 + self.calls * 101

    def noise(self, wavelength):
        salt = self.salt(); c0, r0 = self.origin
        if wavelength / self.px < 8:
            sigma = wavelength / self.px / 2.5; m = int(np.ceil(4 * sigma)) + 1
            iy, ix = np.mgrid[r0 - m:r0 + self.n + m, c0 - m:c0 + self.n + m]
            g = gaussian_filter(hashed_normal(ix, iy, salt).astype('float32'), sigma)[m:-m, m:-m]
            impulse = np.zeros(2 * m + 1); impulse[m] = 1
            return g / (gaussian_filter(impulse, sigma) ** 2).sum()  # exact deviation of blurred unit noise, the same for every tile
        step = wavelength / 3 / self.px  # lattice spacing in samples
        lo_c, lo_r = int(np.floor(c0 / step)) - 8, int(np.floor(r0 / step)) - 8; cells = int(np.ceil(self.n / step)) + 18
        iy, ix = np.mgrid[lo_r:lo_r + cells, lo_c:lo_c + cells]
        coarse = gaussian_filter(hashed_normal(ix, iy, salt), 1.5)
        rows, cols = np.mgrid[0:self.n, 0:self.n]
        g = map_coordinates(coarse, [(rows + r0) / step - lo_r, (cols + c0) / step - lo_c], order=3)
        return (g / LATTICE_DEVIATION).astype('float32')

    def fbm(self, wavelength, octaves=3, gain=.5):
        total = sum(gain ** i * self.noise(wavelength / 2 ** i) for i in range(octaves))
        return total / np.sqrt(sum(gain ** (2 * i) for i in range(octaves)))

    def sample(self, array, rows, cols):
        return map_coordinates(array, [rows, cols], order=1, mode='reflect')

    def warp(self, array, wavelength, amount):
        rows, cols = np.mgrid[0:self.n, 0:self.n].astype('float32')
        return self.sample(array, rows + self.noise(wavelength) * amount / self.px, cols + self.noise(wavelength) * amount / self.px)


LATTICE_DEVIATION = .187  # deviation of unit lattice noise after the sigma-1.5 blur and cubic resampling (measured)


def channel_distance(resolution, span, courses):
    """Signed metres from the channel edge (negative inside) for spline courses with half-widths."""
    px = span / (resolution - 1)
    centre = np.ones((resolution, resolution), bool); half = np.zeros((resolution, resolution), 'float32')
    for points, widths in courses:
        tck, _ = splprep(np.array(points).T, s=0, k=min(3, len(points) - 1))
        t = np.linspace(0, 1, resolution * 4); cx, cy = splev(t, tck)
        w = np.interp(t, np.linspace(0, 1, len(widths)), widths)
        col = np.round((np.array(cx) + span / 2) / px).astype(int); row = np.round((span / 2 - np.array(cy)) / px).astype(int)
        ok = (col >= 0) & (col < resolution) & (row >= 0) & (row < resolution)
        centre[row[ok], col[ok]] = False; half[row[ok], col[ok]] = w[ok]
    dist, (ir, ic) = distance_transform_edt(centre, return_indices=True)
    return (dist * px - half[ir, ic]).astype('float32')


def flow_streaks(f, guide, source, steps, step_m, along=True):
    """Line-integral convolution of `source` along (or across) the gradient of `guide`."""
    gy, gx = np.gradient(guide); mag = np.hypot(gx, gy) + 1e-9
    ux, uy = (gx / mag, gy / mag) if along else (-gy / mag, gx / mag)
    rows0, cols0 = np.mgrid[0:f.n, 0:f.n].astype('float32'); total = source.copy(); step = step_m / f.px
    for sign in (1, -1):
        rows, cols = rows0.copy(), cols0.copy()
        for _ in range(steps):
            dr, dc = f.sample(uy, rows, cols), f.sample(ux, rows, cols)
            rows += sign * step * dr; cols += sign * step * dc
            total += f.sample(source, rows, cols)
    total -= total.mean()
    return total / total.std()


def crumbs(f, density, r_lo, r_hi, squash=.85):
    """Heaped irregular nodules as part of the height surface. Returns relief (m) and a per-nodule tone."""
    mean = (r_lo + r_hi) / 2; cell = mean * 1.9; salt = f.salt(); c0, r0 = f.origin
    # Nodule centres live on a global jittered grid, so a nodule straddling two tiles is the same nodule in both.
    gx, gy = np.meshgrid(np.arange(int(np.floor(c0 * f.px / cell)) - 1, int(np.ceil((c0 + f.n) * f.px / cell)) + 2),
                         np.arange(int(np.floor(r0 * f.px / cell)) - 1, int(np.ceil((r0 + f.n) * f.px / cell)) + 2))
    gx, gy = gx.ravel(), gy.ravel(); draw = lambda k: hashed(gx, gy, salt + k)
    pts = np.column_stack([(gx + draw(1)) * cell - c0 * f.px, (gy + draw(2)) * cell - r0 * f.px])  # local metres
    idx = np.clip((pts / f.px).astype(int), 0, f.n - 1)
    keep = draw(3) < density[idx[:, 1], idx[:, 0]]
    pts = pts[keep]; gx, gy = gx[keep], gy[keep]
    warps = [f.noise(mean * 1.5), f.noise(mean * .5), f.noise(mean * 1.5), f.noise(mean * .5)]  # always drawn, so every tile makes the same calls
    if len(pts) < 8:
        return np.zeros((f.n, f.n), 'float32'), np.zeros((f.n, f.n), 'float32')
    radius = np.clip(mean * np.exp(.5 * np.sqrt(-2 * np.log(draw(4))) * np.cos(2 * np.pi * draw(5))), r_lo * .8, r_hi * 1.25)
    lift = (.5 + .45 * draw(6)) * squash; tone = 2 * draw(7) - 1
    # Each nodule is lopsided: its own stretch, heading and profile from domed to pinched.
    stretch = .68 + .32 * draw(8); heading = np.pi * draw(9); profile = .42 + .3 * draw(10)
    near = gaussian_filter(density, r_hi / f.px) > .004
    rows, cols = np.nonzero(near)
    # Warped query positions break circular outlines into lobed, chipped ones.
    qx = cols * f.px + (warps[0][rows, cols] * .36 + warps[1][rows, cols] * .16) * mean
    qy = rows * f.px + (warps[2][rows, cols] * .36 + warps[3][rows, cols] * .16) * mean
    _, ids = cKDTree(pts).query(np.stack([qx, qy], -1), k=5, workers=-1)
    dx = qx[:, None] - pts[ids, 0]; dy = qy[:, None] - pts[ids, 1]
    ca, sa = np.cos(heading[ids]), np.sin(heading[ids])
    q = 1 - ((dx * ca + dy * sa) ** 2 + ((dy * ca - dx * sa) / stretch[ids]) ** 2) / radius[ids] ** 2
    bump = radius[ids] * lift[ids] * np.clip(q, 0, None) ** profile[ids]
    best = bump.argmax(1); top = np.take_along_axis(bump, best[:, None], 1)[:, 0]
    relief = np.zeros((f.n, f.n), 'float32'); shade = np.zeros((f.n, f.n), 'float32')
    relief[rows, cols] = top
    shade[rows, cols] = np.where(top > 0, np.take_along_axis(tone[ids], best[:, None], 1)[:, 0], 0)
    return relief, shade


def mound_field(f):
    """Rounded, lumpy masses (m) with a lightly pinched, uneven crest line."""
    body = smoothstep(f.warp(f.fbm(.30, 2, .5), .2, .045), -.9, 1.5)
    crest = np.clip(1 - np.abs(f.warp(f.fbm(.36, 2, .4), .2, .05)) / 1.2, 0, 1)
    # Knobs along each crest: the ridge line rises and falls into separate tops.
    knobs = .55 + .45 * smoothstep(f.noise(.085), -1.0, 1.0)
    shoulders = smoothstep(f.noise(.11), -.2, 1.3)
    return body * (.050 + .034 * crest * knobs + .016 * shoulders)


def specimen_inputs(f):
    """Channel course and unshaped land masses laid out after the canyon reference."""
    main = ([(-.80, -.62), (-.42, -.44), (-.12, -.30), (.10, -.08), (.13, .18), (.34, .40), (.62, .52), (.85, .74)],
            [.055, .05, .042, .036, .034, .036, .04, .045])
    branch = ([(.13, .16), (-.06, .38), (-.30, .52), (-.50, .80)], [.016, .022, .026, .03])
    side = ([(.10, -.10), (.36, -.14), (.58, -.02), (.85, .02)], [.016, .02, .024, .028])
    flow = channel_distance(f.n, f.span, [main, branch, side])
    bank = flow + .010 * f.noise(.09) + .003 * f.noise(.025)
    amplitude = .5 + .5 * smoothstep(f.noise(.5), -1.5, .3)
    return (1.35 * amplitude * mound_field(f) + .004).astype('float32'), bank, flow


def style_surface(f, land, bank, flow=None, datum=None, tilled=None, shade=None, tracks=None, blocks=None, true_terrain=False):
    """Shape, crust and finish for a land base height (m) and signed channel-edge distance (m).

    `land` is height above the channel surface; `datum` is that surface's own level (default flat).
    `shade` optionally gives how dark the real ground looks from above (0 light .. 1 dark); crust and
    clay tone then follow it, with noise still breaking the pattern up.
    `tracks` optionally gives road strength 0..1; roads are pressed, smooth, pale lines with no crust.
    `blocks` optionally gives building strength 0..1; buildings are small raised flat-topped blocks.
    `true_terrain` keeps `land` as the landform: no reshaped banks and no added lumps, only surface-scale clay detail.
    `tilled` optionally gives farmland: `mask`, `rows` (-1..1 furrow wave), `edge` and `tone`, each a grid.
    """
    px = f.px; out = np.clip(bank, 0, None)
    farm = np.zeros((f.n, f.n), 'float32') if tilled is None else tilled['mask']
    # Some banks rise as steep cut faces, others as low aprons.
    reach = .024 + .04 * smoothstep(f.noise(.3), -.4, 1.2)
    macro = land * (1 - np.exp(-out / reach)) + .0035 * smoothstep(out, 0, .004)
    macro = gaussian_filter(np.minimum(macro, out * .95 + .004), .010 / px)
    if true_terrain: macro = land + .0035 * smoothstep(out, 0, .004)
    # Pressed lumps, dents and ledges: no face stays a smooth sheet.
    lumps = .012 * f.noise(.06) + .007 * f.noise(.03) + .009 * np.clip(f.noise(.04) - .5, 0, 2) + .003 * np.clip(f.noise(.016) - 1.0, 0, 2) - .004 * np.abs(f.warp(f.noise(.03), .02, .008))
    macro += (0 if true_terrain else 1) * lumps * smoothstep(out, .003, .04) * (.10 + .90 * smoothstep(macro, .006, .035)) * (1 - .9 * farm)
    # Skin: fine pressed grain, sparse pits and short scratches under the sheen.
    scratch = np.clip(np.abs(f.warp(f.noise(.02), .012, .004)) / .05, 0, 1)
    skin = .0009 * f.noise(.0065) + .0006 * f.noise(.0032) + .0003 * f.noise(.0018) + .0009 * np.clip(f.noise(.0028) - .9, 0, 2) - .0006 * np.clip(f.noise(.007) - 1.8, 0, 1.5) - .0005 * (1 - scratch) * smoothstep(f.noise(.1), .3, 1)
    # Cracks and long wiped smears.
    crack_net = np.clip(1 - np.abs(f.warp(f.noise(.028), .012, .006)) / .028, 0, 1) ** 2 * smoothstep(f.noise(.11), -.1, .9)
    wipe = flow_streaks(f, f.noise(.4), f.noise(.0024) + .6 * f.noise(.006), 26, .0025)
    skin *= .3 + .7 * smoothstep(f.noise(.1), -.6, .9)  # worked patches beside smoother ones
    skin += -.0011 * crack_net + .0002 * wipe * smoothstep(f.noise(.14), .2, 1.1)
    broad = gaussian_filter(macro, .006 / px)
    sy, sx = np.gradient(broad, px); slope = np.hypot(sx, sy)
    steep = smoothstep(slope, .55, 1.25)
    relief_top = smoothstep(broad, .03, .11)
    concave = np.clip(gaussian_filter(broad, .012 / px) - broad, -.004, .004) / .004

    # Fall-line flutes on steep faces; soft drag marks elsewhere.
    flutes = flow_streaks(f, broad, f.noise(.0032) + .8 * f.noise(.007), 22, .0022)
    flute_gate = steep * smoothstep(f.noise(.12), -.8, .4)
    clay = macro + (.0030 * f.noise(.015) - .0035 * np.abs(f.noise(.024))) * steep - .0010 * flutes * flute_gate + .0014 * np.clip(flutes - 1.2, 0, 2) * steep - .0005 * flutes * (1 - flute_gate) * smoothstep(slope, .15, .5) + skin * smoothstep(out, 0, .004)

    # Crust gathers in hollows, on aprons and lower flanks; steep faces and tops stay bare.
    patches = f.fbm(.11, 2, .6)
    if shade is None:
        weight = .95 * patches + .9 * concave + .55 * (1 - relief_top) - 1.5 * steep - .75 * relief_top * smoothstep(-concave, .1, .6) + .25
    else:
        # Imagery decides where the dark crust lies; noise and hollows only fray its margins and thin it out.
        weight = 5.0 * (shade - .5) + .12 * patches + .1 * concave + 1.0
    weight += (.35 if shade is None else .1) * f.noise(.012)
    crust = smoothstep(weight, .75, 1.25) * smoothstep(out, .0, .012 if shade is None else .004) * (1 - farm)
    road = np.zeros((f.n, f.n), 'float32') if tracks is None else tracks
    built = np.zeros((f.n, f.n), 'float32') if blocks is None else blocks
    crust = crust * (1 - road) * (1 - built)
    piles = smoothstep(f.noise(.035) + .5 * f.noise(.014), -.55, .35)
    heap = gaussian_filter(crust * piles, .004 / px) * .0045
    coarse, tone_a = crumbs(f, np.clip(crust * (.05 + .95 * piles) * .9, 0, 1), .0028, .0058)
    mid, tone_m = crumbs(f, np.clip(crust * (.3 + .7 * piles) * 1.1, 0, 1), .0015, .0030)
    fine, tone_b = crumbs(f, np.clip(crust * 1.1, 0, 1), .0008, .0017)
    grit, _ = crumbs(f, np.clip(.01 + .07 * smoothstep(f.noise(.07), .3, 1.4) - crust, 0, 1) * (bank > .002) * (slope < .4), .0007, .0016, squash=.6)
    nodules = np.maximum(np.maximum(coarse, mid), fine) * (1 + .10 * f.noise(.0014))
    height = clay + np.clip(heap, 0, None) + nodules + grit
    # Roads are scored grooves with a raised lip, unlike the flat sunken water.
    height = height - .0016 * road + .0007 * road * (1 - road) * 4
    height = height + .0022 * built
    if tilled is not None:
        # Combed rows inside each parcel and a pressed groove along its boundary.
        height += farm * .00055 * tilled['rows'] * (1 + .25 * f.noise(.03)) - .0011 * tilled['edge']

    # Channel: flat silt with flow streaks, hairline cracks and a soft lip at the bank.
    inside = smoothstep(-bank, -.002, .004) if shade is None else smoothstep(-bank, -.0006, .0012)
    silt = flow_streaks(f, gaussian_filter(bank if flow is None else flow, .012 / px), f.noise(.004), 30, .003, along=False)
    cracks = np.clip(1 - np.abs(f.warp(f.noise(.035), .008, .004)) / .02, 0, 1) * smoothstep(f.noise(.15), .4, 1.2)
    bed = .00009 * silt + .00012 * f.noise(.006) - .00015 * cracks + .0010 * np.exp(-np.clip(-bank, 0, None) / .004) - .0012
    height = height * (1 - inside) + bed * inside
    level = np.zeros((f.n, f.n), 'float32') if datum is None else datum
    height = height + level

    # Intrinsic colour (linear). Ochre shows on worn steep faces, taupe coats the rest.
    cover = smoothstep(nodules, .0002, .0009); stain = np.clip(gaussian_filter(crust, .006 / px) * 1.2, 0, 1)
    ochre_w = np.clip((.15 + .85 * steep) * smoothstep(f.fbm(.18, 2), -.5, .9) + .15 * relief_top - .9 * stain, 0, 1) * (.72 + .28 * smoothstep(f.noise(.022), -1, 1))
    dust_w = smoothstep(f.noise(.08), -.3, .9) * (1 - steep) * (1 - relief_top) * (1 - stain)
    if shade is not None:
        dust_w = np.clip(.35 * dust_w + 1.5 * (.45 - shade), 0, 1) * (1 - stain)
    ochre = np.array([.340, .215, .092]); taupe = np.array([.205, .155, .105]); dark = np.array([.130, .110, .090])
    crumb = np.array([.112, .100, .088]); dust = np.array([.260, .200, .140]); silt_c = np.array([.400, .350, .280])
    mix = lambda a, b, w: a * (1 - w[..., None]) + b * w[..., None]
    colour = mix(np.broadcast_to(taupe, (f.n, f.n, 3)), ochre, ochre_w)
    colour = mix(colour, dust, dust_w * .4)
    colour = mix(colour, dark, stain * .8)
    if shade is not None:
        colour = colour * (1.12 - .3 * shade)[..., None]
    colour = mix(colour, ochre * .7, np.clip(road * 1.3, 0, 1))  # scored ochre edge
    colour = mix(colour, dust * 1.45, smoothstep(road, .55, .95))  # pale worn bed, so a road cannot be missed or mistaken for water
    colour = mix(colour, dust * 1.25, built)  # scoring exposes ochre clay; water stays pale
    if tilled is not None:
        # Parcels differ in tone as the real fields do; palette stays within the reference clay and dust.
        parcel = dust[None, None, :] * (.72 + .5 * tilled['tone'])[..., None]
        colour = mix(colour, parcel, farm * .7) * (1 - .10 * farm * np.clip(-tilled['rows'], 0, 1) - .22 * tilled['edge'])[..., None]
    colour = mix(colour, crumb, cover) * (1 + .14 * (tone_a + tone_m + tone_b) * cover)[..., None]
    colour = colour * (1 + .07 * f.noise(.03) + .05 * f.noise(.006) - .20 * flutes * flute_gate - .22 * crack_net + .02 * wipe * (1 - cover))[..., None]
    colour = mix(colour, silt_c * (1 + .07 * silt + .04 * f.noise(.05) - .06 * cracks)[..., None], inside)
    roughness = .40 + .07 * f.noise(.04) + .05 * f.noise(.008) + .12 * dust_w + .26 * cover + .08 * stain + .1 * farm + .3 * road
    roughness = roughness * (1 - inside) + (.66 + .04 * silt) * inside
    return {'height': height.astype('float32'), 'base_color': np.clip(colour, 0, 1).astype('float32'),
            'roughness': np.clip(roughness, .28, .92).astype('float32'), 'crust': crust.astype('float32'),
            'nodules': (nodules * (1 - inside)).astype('float32'), 'channel': inside.astype('float32'),
            # Water is its own surface: level (m), signed bank distance (m) and road mask travel with the terrain.
            'water_level': (level - .0004).astype('float32'), 'bank': bank.astype('float32'), 'road': road.astype('float32')}


def author_specimen(resolution=2400, span=1.6, seed=404):
    f = Fields(resolution, span, seed)
    land, bank, flow = specimen_inputs(f)
    return style_surface(f, land, bank, flow)


def write_maps(output, maps, manifest):
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    np.savez(output / 'surface.npz', **maps)
    c = maps['base_color']; srgb = np.where(c <= .0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - .055)
    Image.fromarray(np.uint8(np.clip(srgb, 0, 1) * 255)).save(output / 'base-color.png')
    lo, hi = float(maps['height'].min()), float(maps['height'].max())
    Image.fromarray(np.uint16((maps['height'] - lo) / (hi - lo) * 65535)).save(output / 'height.png')
    for key in ['roughness', 'crust', 'channel', 'road']:
        Image.fromarray(np.uint8(maps[key] * 255)).save(output / f'{key}.png')
    # Water shader inputs: R mask, G distance from bank (0 at the edge, 1 at 10 mm), B unused; flow map RG = downstream direction.
    depth = np.clip(-maps['bank'] / .01, 0, 1)
    Image.fromarray(np.uint8(np.dstack([maps['channel'], depth, np.zeros_like(depth)]) * 255)).save(output / 'water-mask.png')
    if 'flow_dir' in maps:
        Image.fromarray(np.uint8(np.dstack([maps['flow_dir'] * .5 + .5, np.zeros_like(depth)]) * 255)).save(output / 'water-flow.png')
    (output / 'manifest.json').write_text(json.dumps({**manifest, 'resolution': int(maps['height'].shape[0]),
        'height_range_m': [lo, hi], 'colour_space': 'base colour PNG sRGB; remaining images linear data',
        'water': {'mask': 'water-mask.png (R mask, G bank distance over 10 mm)', 'flow': 'water-flow.png (RG = downstream unit vector, +R east, +G south, 0.5 = zero)',
            'level': 'surface.npz water_level, metres', 'material': 'separate object and material named Water in the render scene'}}, indent=2) + '\n')


def write_specimen(output, resolution, span=1.6, seed=404):
    write_maps(output, author_specimen(resolution, span, seed), {'kind': 'image-matched relief specimen',
        'reference': 'docs/reference/style-studies/04-canyon.png', 'span_m': span, 'seed': seed,
        'note': 'Not San Luis terrain. Colour holds no baked light.'})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--resolution', type=int, default=2400); parser.add_argument('--seed', type=int, default=404)
    args = parser.parse_args(); write_specimen(args.output, args.resolution, seed=args.seed)
