# 03 — Shape the hand-modelled relief

## Goal

From the browser, low terraces and banks read clearly and mountain ridges look like rounded hand-pinched clods.

## Scope

- **Bake:** apply a tweakable non-linear height curve and low-amplitude rounded clod displacement before each LOD mesh; retain seam-safe edges.
- **Tiles:** rebuild affected GLBs, bounds, skirts, and geometric errors.
- **Viewer:** expose the curve in the debug panel and load regenerated tiles with the existing flat material.

## Acceptance criteria

- The debug curve values used for a build are recorded; a rebuild visibly boosts low relief and compresses high relief against the 02 baseline.
- Fixed oblique mountain and bank screenshots satisfy **S1**: rounded, stacked-looking ridges rather than sharp crests, and abrupt banks where water will meet land.
- Panning and LOD changes show no new seams or discontinuities; major San Luis landforms remain recognisable.

## Blocked by

02.

## Notes

Water surfaces arrive in 05. Here, inspect future shoreline bank positions against hydrography overlays without inventing water geometry.

## Status

**Implemented; S1 visual criterion remains open.** The manifest records gain 5, 800 m knee, 60 m clod amplitude, 60 m rounding and 5,500 m edge falloff; the debug panel exposes the baked curve. Shape tests passed in the 27-test Python suite. [04-culebra-range.jpg](../evidence/04-culebra-range.jpg) and [05-rio-grande-gorge.jpg](../evidence/05-rio-grande-gorge.jpg) show boosted relief and banks, but the ridges still read smoother and more regular than the hand-pinched reference. Full LOD seam inspection and a side-by-side pre-remap comparison remain unverified.
