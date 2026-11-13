"""Draw what the relief will contain over the aerial photograph, for review before rendering.

Writes OUTPUT/reference/naip-overlay.jpg (cyan river, yellow tributaries, magenta ponds, orange roads)
and naip-fields.jpg (detected parcels with their row direction).
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from bake.style.fields import field_parcels, woody_cover
from bake.style.relief_patch import channel_samples, patch_terrain


def write_checks(package, output, min_cells=500, creek_half_m=6, gully_half_m=2.5):
    reference = Path(output) / 'reference'; photo = Image.open(reference / 'naip.jpg').convert('RGB')
    cir = Image.open(reference / 'naip-cir.png').convert('RGB')
    woody = woody_cover(cir); terrain, _ = patch_terrain(package, reference, woody)
    samples, _, size = channel_samples(package, min_cells, creek_half_m, gully_half_m, woody=woody, terrain=terrain)
    scale = photo.width / size; half = size / 2; overlay = photo.copy(); draw = ImageDraw.Draw(overlay)
    for feature in json.loads((reference / 'roads.geojson').read_text())['features']:
        draw.line([((x + half) * scale, (z + half) * scale) for x, z in feature['geometry']['coordinates']], fill=(255, 120, 0), width=2)
    for x, z, width, _ in samples:
        colour = (0, 255, 255) if width == creek_half_m else (255, 0, 255) if width == 3 else (255, 255, 0)
        draw.point(((x + half) * scale, (z + half) * scale), fill=colour)
    overlay.save(reference / 'naip-overlay.jpg', quality=88)
    ids, parcels = field_parcels(cir, size); pixels = np.asarray(photo).copy()
    palette = np.random.default_rng(1).integers(60, 255, (len(parcels) + 1, 3)); farmed = ids > 0
    pixels[farmed] = (pixels[farmed] * .45 + palette[ids[farmed]] * .55).astype('uint8'); fields = Image.fromarray(pixels); draw = ImageDraw.Draw(fields)
    for parcel in parcels:
        x, y = parcel['centre_px']; along = parcel['row_normal_rad'] + np.pi / 2
        draw.line((x - 40 * np.cos(along), y - 40 * np.sin(along), x + 40 * np.cos(along), y + 40 * np.sin(along)), fill=(255, 255, 255), width=3)
    fields.save(reference / 'naip-fields.jpg', quality=88)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--package', type=Path, default=Path('data/style-patch'))
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args(); write_checks(args.package, args.output)
