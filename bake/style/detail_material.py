"""Tileable close-range dirt-and-mud detail for the relief tiles: what the ground shows within a few metres.

One square of ground (default 6.875 m, which divides every tile side exactly) with clods, pebbles, cracks
and grain. Writes a tangent-space normal map and a colour multiplier; both repeat seamlessly.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image

SPAN_M = 112640 / 2 ** 14


def band(rng, n, span_m, wavelength_m, width=.45):
    """Periodic noise concentrated around one wavelength; unit deviation."""
    f = np.hypot(*np.meshgrid(np.fft.fftfreq(n, span_m / n), np.fft.fftfreq(n, span_m / n)))
    shape = np.exp(-.5 * (np.log(np.maximum(f, 1e-9) * wavelength_m) / width) ** 2); shape[0, 0] = 0
    field = np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * shape).real
    return (field / field.std()).astype('float32')


def step(v, lo, hi):
    t = np.clip((v - lo) / (hi - lo), 0, 1); return t * t * (3 - 2 * t)


def author_detail(resolution=2048, span_m=SPAN_M, seed=77):
    rng = np.random.default_rng(seed); n = resolution; b = lambda w, width=.45: band(rng, n, span_m, w, width)
    # Heights in metres. Clods: broken lumps of dried mud; pebbles: small stones pressed in; cracks; grain.
    clod_field = b(.75) + .5 * b(.33); clods = .035 * step(clod_field, -.2, 1.3) + .012 * b(1.9)
    pebble_field = b(.11, .3) + .4 * b(.06, .3); pebbles = .012 * step(pebble_field, 1.0, 1.9)
    crack_field = np.abs(b(1.3, .35) + .35 * b(.5, .35)); cracks = (1 - step(crack_field, 0, .07)) * step(b(3.0), -.3, .6)
    grain = .0016 * b(.022, .5) + .0025 * b(.045, .5)
    height = clods + pebbles - .02 * cracks + grain
    px = span_m / n
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / (2 * px); gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) / (2 * px)
    normal = np.dstack([-gx, gy, np.ones_like(gx)]); normal /= np.linalg.norm(normal, axis=2, keepdims=True)  # glTF: +Y is image up
    # Colour multiplier around 1: dusty tops lighter, hollows and cracks darker, each clod its own tone.
    cavity = np.clip((height - np.fft.ifft2(np.fft.fft2(height) * np.exp(-(np.hypot(*np.meshgrid(np.fft.fftfreq(n, px), np.fft.fftfreq(n, px))) * .25) ** 2)).real) / .02, -1, 1)
    tone = 1 + .10 * cavity + .07 * b(.6) * step(clod_field, -.2, .6) + .05 * b(2.5) - .35 * cracks + .10 * step(pebble_field, 1.0, 1.9) * b(.2)
    return normal.astype('float32'), np.clip(tone, .45, 1.35).astype('float32'), height.astype('float32')


def write_detail(output, resolution=2048):
    output = Path(output); output.mkdir(parents=True, exist_ok=True); normal, tone, height = author_detail(resolution)
    Image.fromarray(np.uint8(np.clip(normal * .5 + .5, 0, 1) * 255 + .5)).save(output / 'dirt-normal.png')
    # An overlay map: linear 0.5 leaves the tile colour unchanged, so the file holds sRGB-encoded tone / 2.
    half = np.clip(tone / 2, 0, 1); srgb = np.where(half <= .0031308, 12.92 * half, 1.055 * half ** (1 / 2.4) - .055)
    Image.fromarray(np.uint8(np.repeat(srgb[..., None], 3, 2) * 255 + .5)).save(output / 'dirt-tone.png')
    (output / 'detail.json').write_text(json.dumps({'span_m': SPAN_M, 'resolution': resolution, 'height_range_m': [float(height.min()), float(height.max())],
        'normal': 'dirt-normal.png (tangent space, glTF convention)', 'tone': 'dirt-tone.png (sRGB overlay map: linear 0.5 = no change)',
        'use': 'repeat every span_m of ground; tile sides are exact multiples of span_m, so the pattern is continuous across tiles and levels'}, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True); parser.add_argument('--resolution', type=int, default=2048)
    args = parser.parse_args(); write_detail(args.output, args.resolution)
