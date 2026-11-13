# 01 — Render one San Luis terrain tile

## Goal

A visitor opens the browser and sees a small, flat-shaded San Luis DEM patch as a 3D tile, and can orbit it.

## Scope

- **Bake:** fetch a small USGS 3DEP 10 m patch around San Luis; mesh one terrain patch and export one GLB.
- **Tiles:** emit a minimal valid `tileset.json` that references the GLB.
- **Viewer:** load it with PlayCanvas + 3DTilesRendererJS (PlayCanvas renderer), use flat shading and a fixed oblique starting camera.

## Acceptance criteria

- A documented one-command bake regenerates the GLB and tileset from downloaded input; source DEM is not committed.
- A local static-file server serves the tileset and the browser displays the patch with no failed tile requests or console errors.
- A screenshot from the fixed starting camera shows relief derived from the San Luis DEM, with orbit interaction working.
- The initial camera is oblique and looks down/across the patch, establishing the **S6** reference viewpoint even before materials and lighting are added.

## Blocked by

None.

## Notes

Keep this slice intentionally small. It proves data → GLB → OGC tileset → actual renderer → pixels before adding styling or quadtree complexity.

## Status

**Implemented; functional acceptance verified.** `UV_CACHE_DIR=/private/tmp/san-luis-uv-cache uv run python -m bake --output data/ticket01-check` regenerated a 12 km, 10 m USGS tile (119,546 triangles) on 12 November 2026. The local PlayCanvas browser smoke check recorded one loaded GLB, an orbit camera change, and zero failed requests or exceptions in `data/evidence-first-slice/browser.json`; the fixed oblique capture is [01-first-tile.png](../evidence/01-first-tile.png). Source DEM and generated GLB remain ignored under `data/` and `public/terrain/`. The current browser host was unavailable for an additional fresh capture; the saved smoke evidence is from this workspace session.
