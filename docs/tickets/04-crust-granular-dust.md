# 04 — Render two-tone aged model material

## Goal

The browser terrain looks like dusty ochre crust over dark, crumbly relief, with crevices shaded by a warm low sun.

## Scope

- **Bake:** derive per-tile crust/granular and dust channels from curvature, slope, aspect, and clumpy noise; bake vertex AO; generate shared crust and granular albedo/normal textures.
- **Tiles:** pack a ~256² KTX2 mask per tile and shared tiling 512² KTX2 material sets alongside rebuilt GLBs.
- **Viewer:** swap a custom two-scale mud material on tile load; use one fixed warm low directional sun and no realtime shadows.

## Acceptance criteria

- Fixed mountain and valley-floor screenshots satisfy **S2, S3, S6**: smoother tan convex tops, dark pitted concavities and steep/shaded faces, irregular blend edges, pale dust strongest on upward flats, and dark AO crevices.
- Sampled crust, granular, mid-tone, and dust colours are recorded against the **S7** starting palette; differences are visible in a side-by-side reference sheet.
- Inspecting tile assets shows the per-tile mask and shared KTX2 sets; material remains aligned across tile and LOD seams.
- Viewer shows the new material after a cold load, including tiles that stream in later.

## Blocked by

03.

## Notes

The Relief Pfyffer photograph is the texture and lighting target. Author detail textures offline; do not crop or ship the photograph.

## Status

**Implemented; S2/S3/S6/S7 fidelity remains open.** The bake writes a 256² KTX2 mask per tile and four shared 512² KTX2 detail textures. Curvature, slope, aspect, clumpy detail and AO drive the streamed custom material; `npm run validate:assets` passed 341 tiles. [04-culebra-range.jpg](../evidence/04-culebra-range.jpg) and [08-close.jpg](../evidence/08-close.jpg) show both tones, but the dark texture forms repetitive patches and the surface looks too smooth and even against the photograph. Starting target colours are in `docs/design.md`; a full image-picked six-colour comparison and visual sign-off remain unverified.
