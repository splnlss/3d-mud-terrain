# 11 — Sign off against the Relief Pfyffer reference

## Goal

A reviewer can inspect a repeatable side-by-side comparison and see a San Luis diorama that reads as a close-up of the reference model.

## Scope

- **Bake:** make final targeted adjustments to clod shape, masks, AO, palette, water rim/grain, and detail; regenerate affected tiles.
- **Tiles:** publish and validate the final GLBs/KTX2/tileset and provenance manifest.
- **Viewer:** lock fixed camera poses and colour/lighting settings, capture stills and water clip, and confirm performance after adjustments.

## Acceptance criteria

- A comparison sheet pairs the reference with fixed-camera mountain, bank, valley-floor, and water screenshots at stated viewport/exposure; each **S1–S7** criterion has a pass/fail mark and evidence crop.
- Colour-picked reference swatches and representative rendered swatches are recorded for ochre, tan, dark granular, mid grey-brown, dust, and water; any departure from the source image is documented and corrected before sign-off.
- A short water clip confirms subtle shimmer without a glossy or reflective read. Named San Luis landmarks remain recognisable.
- Final static tileset passes validation, and the 10 mobile performance measurements still pass after the final bake/viewer changes.

## Blocked by

10.

## Notes

Use the photograph as the visual authority, not generic mud examples. Close the ticket only when every style checklist item and performance gate passes.

## Status

**Blocked on style review and ticket 10.** The portable [comparison sheet](../evidence/comparison.html) places fixed captures beside [the authoritative photograph](../reference/relief-pfyffer.png) and records S1–S7 assessments. Water samples are in `docs/reference/palette.json`; the local 8-second clip is `data/evidence-final-desktop/water-shimmer.webm`. Current captures show smoother, more regular relief and dark patches than the physical model, weak pivot/detail visibility, and narrow bright water channels. S1–S7 cannot honestly be marked passed; six representative reference/rendered swatches, independent visual sign-off, and the two physical-phone performance runs remain open. The static 341-tile validator passes, but that does not close this ticket.
