# 10 — Meet the mobile delivery budget

## Goal

The finished diorama loads quickly and stays smooth while a phone visitor pans and zooms through the full extent.

## Scope

- **Bake:** tune LOD errors, mesh density, masks, shared textures, and compression without losing reference characteristics.
- **Tiles:** republish size-optimised GLBs/KTX2 and quadtree metadata; keep skirts, water primitives, and static hosting valid.
- **Viewer:** tune tile selection/cache and material cost, then record mobile frame, memory, transfer, and draw-call counters.

## Acceptance criteria

- On iPhone 12 and a Snapdragon 7-series class phone at native resolution, the PRD's 60-second trace meets **≥60 fps average and ≤16.7 ms for ≥95% of frames**, **<150 MB peak GPU allocation estimate**, and **≤200 draw calls/frame**.
- Empty-cache first meaningful terrain render transfers **<5 MB compressed**, including viewer assets and tiles; evidence includes network log and timing.
- Fixed before/after views still satisfy **S1–S7**; speed changes do not flatten clods, erase granular detail, gloss water, or create LOD seams.
- Record device/browser/resolution, trace, measurements, and final tile-size breakdown in a reproducible report.

## Blocked by

06, 07, 08, 09.

## Notes

Use the production build and real target devices; desktop emulation does not establish the budget. Prefer optimising tile selection and baked assets before adding runtime passes.

## Status

**Blocked on target hardware.** Desktop production traces in [validation.md](../validation.md) recorded 84.04 fps, 99.96% frames ≤16.7 ms, 22 peak draws, 87.36 MB estimated GPU allocation and 3.60 MB cold first-view transfer. A phone-size viewport on the same Apple M3 Pro recorded 86.37 fps, 99.94%, 9 draws and 76.98 MB. These are not iPhone 12 or Snapdragon 7-series measurements. The required 60-second native-resolution traces, device/browser details, cold-cache logs and final style-preservation comparison cannot be signed off without those devices and S1–S7 approval.

The numeric figures above are historical diagnostics from before the independent
review corrections. The current [validation report](../validation.md) supersedes
them, preserves the host-presentation caveats, and still leaves both physical
phone gates open.
