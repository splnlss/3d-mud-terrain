# 08 — Add miniature flecks and strands

## Goal

Close inspection reveals occasional rust-red miniature-like flecks and fine pale strands on the model surface.

## Scope

- **Bake:** procedurally place or encode sparse flecks/strands in tile detail inputs, avoiding mapped roads/buildings and water interiors.
- **Tiles:** repack affected KTX2 detail/mask assets with deterministic placement across tile borders and LODs.
- **Viewer:** render the detail through the existing material without extra object draw calls.

## Acceptance criteria

- Fixed close crops satisfy **S5**: sparse rust-orange/red points and thin pale lines visible at close range, absent as dominant patterns at the default view.
- Details do not form a geographic road/building layer, repeat conspicuously at tile boundaries, or pop abruptly with LOD.
- Regenerated tiles display the same detail placement in the browser and preserve **S2, S3, S7** material balance.

## Blocked by

04, 07.

## Notes

The villages/paths decision remains open in the PRD. This slice implements the current non-geographic approximation only.

## Status

**Implemented; S5 visual criterion remains open.** A seeded shared atlas encodes rust flecks and thin pale strands without mapped human features or extra draw calls; material tests passed. [08-close.jpg](../evidence/08-close.jpg) is the fixed close crop. The marks are too difficult to distinguish there for an S5 pass, and repetition/LOD pop has not been fully inspected. The PRD's geographic-villages decision remains open; this implementation uses only the agreed non-geographic approximation.
