# Relief specimen: image-matched study (2026-11-12)

**Not visually accepted. Not San Luis geometry.** A 1.6 m calibration specimen
authored against [reference 04](../../reference/style-studies/04-canyon.png),
checked against 01 and 03. User judgement is still required.

| Board | Reference | Render |
|---|---|---|
| [Canyon](compare-canyon.jpg) | 04 | [sharp](canyon-sharp.jpg), [neutral clay](canyon-clay-sharp.jpg) |
| [Elevated](compare-elevated.jpg) | 01 | [elevated](elevated-sharp.jpg) |
| [Overhead](compare-overhead.jpg) | 03 | [overhead](overhead-sharp.jpg) |

Sharp captures only; depth of field is deferred by user decision. The same recipe
on real terrain: [Culebra Creek patch](../relief-patch/README.md).

Source: `bake/style/relief_study.py` (authoring), `bake/style/blender_relief_study.py`
(render), settings JSON beside each image. One continuous 3200² surface
(0.5 mm samples); crust nodules, flutes and clay grain are geometry. Colour and
roughness come from the same fields, with no generated image or baked light.

```sh
scripts/relief_study.sh 3200 96 canyon:--sharp canyon:--sharp:--clay elevated:--sharp overhead:--sharp
uv run python scripts/relief_boards.py
```

## What changed against the rejected attempts

- Crust is connected patches of heaped nodules in hollows and on lower flanks,
  with ragged margins, instead of scattered plates or dots.
- Land is crest lines with saddles and pressed lumps, instead of stamped cones.
- Clay, ochre faces, dark crust and pale channel separate in value as in 01/03.

## User review, 2026-11-12

Direction accepted as "good". The user agreed mound shape, clay detail and nodules
were still off (cracks are acceptable), asked that channels follow the source
terrain and DEM, and deferred depth of field. Later passes: rounded `mound_field`
masses, lopsided three-size nodules, cracks and wiped smears, grain varying
between worked and smooth patches. A ledge term was tried and removed because it
drew contour-like rings.

## Remaining self-assessed gaps

- Nodules are still more uniform than the reference crumbs.
- Reference clay has more drips and broken edges.
- Lighting lacks the strong golden glow.

Editing any noise call reshuffles later fields for the same seed.
