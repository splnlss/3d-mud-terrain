# 06 — Add restrained painted-water motion

## Goal

Water retains the flat painted-plaster look while a visitor notices faint, slow drifting glints.

## Scope

- **Bake:** generate fine grain, shoreline-rim, and wet-band inputs from the baked water polygons and adjacent terrain.
- **Tiles:** repack affected water/terrain GLB attributes or textures without adding a water draw pass.
- **Viewer:** use one-pass matte water shading with faint rim, fine grain, slight fresnel lift, two scrolling low-frequency normals, tight sun glints, slow pulse, and wetness control.

## Acceptance criteria

- A fixed shoreline still and short clip satisfy **S4**: pale warm matte sheet, faint darker rim, sharp contact, fine texture, and subtle moving shimmer that does not read as reflective glass.
- Wetness and water level controls visibly affect their intended surfaces without opening shoreline gaps.
- Water uses one pass and no reflection/refraction buffers; a tile still targets terrain plus water as two draws before any renderer overhead.
- The same water appearance persists as tiles stream or change LOD.

## Blocked by

05.

## Notes

Compare clips at normal playback speed, not only paused frames; still-frame palette remains close to water `#EFE0C7` from colour-picked reference water; see `../reference/palette.json`.

## Status

**Implemented; animated style sign-off remains open.** One water shader pass supplies rim, grain, two scrolling normals, restrained glints and pulse; no reflection/refraction target is allocated. [06-sanchez-reservoir.jpg](../evidence/06-sanchez-reservoir.jpg) records the matte still. An 8-second local clip is at `data/evidence-final-desktop/water-shimmer.webm`; it is ignored by git and must be regenerated with `scripts/check-browser.mjs` for review. Wetness and ±1 m level controls exist, but a reviewer has not signed off the moving result or checked every streamed LOD.
