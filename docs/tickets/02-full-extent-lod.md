# 02 — Stream the full valley at multiple LODs

## Goal

A visitor can pan across the complete San Luis Valley diorama and recognise its major mountain and valley shapes while detail streams in.

## Scope

- **Bake:** acquire the full 70 × 70 mi 3DEP DEM, apply per-LOD error bounds, and mesh adaptive Delatin TINs with skirts.
- **Tiles:** export meshopt-compressed, `KHR_mesh_quantization` GLBs in an implicit quadtree with correct bounds and geometric errors.
- **Viewer:** stream and replace LODs while panning/zooming; retain the flat-shaded material from 01.

## Acceptance criteria

- Coverage spans the square centred on 37.20 N, 105.42 W, includes the New Mexico portion, and reaches roughly 15 km past Alamosa.
- Static hosting alone serves the implicit tileset; tile validation passes and the viewer loads without runtime Google or application-server requests.
- A browser flyover reveals the Sangre de Cristo/Culebra relief and valley floor; LOD changes show no cracks, missing patches, or obvious z jumps.
- A fixed-camera screenshot and tile-request log demonstrate coarse first view followed by higher-detail tiles.
- That screenshot keeps the oblique **S6** composition and preserves the broad rounded-form basis needed for **S1** at every LOD; final clod shaping is deferred to 03.

## Blocked by

01.

## Notes

Keep the same end-to-end bake command and viewer route as 01. Record chosen LOD errors in the bake manifest for later tuning.

## Status

**Implemented; seam inspection remains open.** The cached scene has a 112.64 km square at 10 m source spacing, five implicit-quadtree LODs, 341 meshopt/quantized GLBs and skirts. `npm run validate:assets` passed all 341 tiles with no errors or warnings on 12 November 2026. The manifest records LOD TIN errors of 120/60/30/15/7.5 m. The saved browser request log in `data/evidence-final-desktop/browser.json` records child-LOD requests; [09-overview.jpg](../evidence/09-overview.jpg) shows the oblique broad terrain. A complete real-device flyover and visual check of every LOD transition remains unverified.
