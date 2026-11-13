"""Copy relief renders into docs/reviews and pair each with its reference image."""
from pathlib import Path
from PIL import Image, ImageDraw

REFS = Path('docs/reference/style-studies')
SETS = {  # source folder -> (review folder, label, [(reference, render)])
    'data/relief-study': ('docs/reviews/relief-study', 'relief specimen (not San Luis geometry)',
        [('04-canyon', 'canyon-sharp'), ('01-braided-channels', 'elevated-sharp'), ('03-overhead-delta', 'overhead-sharp')]),
    'data/relief-patch': ('docs/reviews/relief-patch', 'Culebra Creek patch (real DEM and mapped creek)',
        [('04-canyon', 'creek-sharp'), ('01-braided-channels', 'elevated-sharp'), ('03-overhead-delta', 'overhead-sharp')]),
}
for source, (review, label, pairs) in SETS.items():
    source, review = Path(source), Path(review); review.mkdir(parents=True, exist_ok=True)
    for old in review.glob('*.jp*g'): old.unlink()
    for old in review.glob('*-settings.json'): old.unlink()
    for render in sorted(source.glob('*-settings.json')):
        name = render.name.removesuffix('-settings.json')
        Image.open(source / f'{name}.png').convert('RGB').save(review / f'{name}.jpg', quality=90)
        (review / render.name).write_text(render.read_text())
    for ref, view in pairs:
        a = Image.open(REFS / f'{ref}.png').convert('RGB'); b = Image.open(source / f'{view}.png').convert('RGB')
        h = 720; a = a.resize((round(a.width * h / a.height), h)); b = b.resize((round(b.width * h / b.height), h))
        board = Image.new('RGB', (a.width + b.width + 12, h + 34), (20, 20, 20)); board.paste(a, (0, 34)); board.paste(b, (a.width + 12, 34))
        draw = ImageDraw.Draw(board); draw.text((8, 10), f'REFERENCE {ref}', fill=(230, 230, 230))
        draw.text((a.width + 20, 10), f'RENDER {label}: {view}', fill=(230, 230, 230))
        board.save(review / f'compare-{view.removesuffix("-sharp")}.jpg', quality=88)

# Aerial photograph beside the overhead render of the same square, plus the source checks.
patch = Path('data/relief-patch'); aerial = patch / 'reference/naip.jpg'
if aerial.exists() and (patch / 'overhead-sharp.png').exists():
    a = Image.open(aerial).convert('RGB').resize((900, 900)); b = Image.open(patch / 'overhead-sharp.png').convert('RGB')
    b = b.resize((round(b.width * 900 / b.height), 900)); board = Image.new('RGB', (a.width + b.width + 10, 900), (20, 20, 20))
    board.paste(a, (0, 0)); board.paste(b, (a.width + 10, 0)); board.save('docs/reviews/relief-patch/compare-aerial.jpg', quality=88)
    for name in ['naip-overlay', 'naip-fields']:
        if (patch / f'reference/{name}.jpg').exists():
            Image.open(patch / f'reference/{name}.jpg').save(f'docs/reviews/relief-patch/source-check-{name.removeprefix("naip-")}.jpg', quality=88)
