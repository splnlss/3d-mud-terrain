# Implementation progress

Authority: [PRD](prd.md), [design](design.md), [vertical slices](tickets/README.md).

Baseline `d90ec9a` contained the skill kit. The historical chat stopped at the PRD
handoff; the current workspace already contained the PRD, eleven tickets, design,
and saved reference image. Implementation continues in this isolated worktree.
The user's subsequent engine decision supersedes the original three.js runtime:
**PlayCanvas 2.24.0, WebGL2, 3DTilesRendererJS's PlayCanvas adapter**.

## Slice status

| Slice | Implementation | Remaining acceptance |
|---|---|---|
| 01 First tile | Real 12 km USGS patch, adaptive TIN, GLB, PlayCanvas orbit. Separate diagnostic browser check passed. | None identified in the functional smoke check. |
| 02 Full extent / LOD | 112.64 km square, five LODs, 341 meshopt GLBs, implicit quadtree, skirts. | Broader real-device LOD seam inspection. |
| 03 Relief | Global height remap, ridge rounding, deterministic clods, edge falloff. | Reference morphology review. |
| 04 Material | Curvature/slope/aspect masks, dust, vertex AO, shared KTX2 crust/gravel details. | Reference fidelity review. |
| 05 Water geometry | NHD perennial rivers/canals/lakes and Sentinel water; canonical shores, islands, DEM levels, carved bed. | Inspect all mapped reaches and real-device seams. |
| 06 Shimmer | One-pass opaque warm pale water, scrolling normals, subtle glints, rim and grain. Recorded local clip. | Animated visual sign-off. |
| 07 Fields | Sentinel reflectance reduced to muted tonal variation; NDWI feeds water mask. | Pivot legibility in final visual review. |
| 08 Sparse details | Procedural rust flecks and thin pale strands in shared atlas. | Verify their scale/sparsity against the photograph. |
| 09 Camera / edge | Constrained orbit, pan/zoom, touch/keyboard, portrait framing, fixed landmark poses, fading edge. | Physical phone gesture check. |
| 10 Performance | Production network captures and 60-second recorder; bounded tile cache and compressed assets. | **iPhone 12 and Snapdragon 7-series hardware measurements. Desktop/emulation do not close this ticket.** |
| 11 Fidelity | Fixed-camera stills, water clip, image-picked water palette, comparison package. | **Independent review and S1–S7 visual sign-off. Not complete.** |

## Data and reproducibility

- USGS 1/3 arcsecond DEMs are window-read and reprojected to EPSG:32613.
  Native resolution, source URLs, identities and cached raster hashes are recorded.
- Public Sentinel-2 summer scenes supply NDVI/NDWI, with cloud/SCL filtering.
- USGS staged HU4 NHD GeoPackages are read within downloaded zip archives, without
  extracting their large databases. Source hashes and catalog metadata are retained. Only named main canals/acequias
  are rendered; drains/laterals/unnamed ditches are omitted, and canals are 20 m wide.
- A completed bake replaces the previous generated scene only after all stages,
  compression and metadata writes succeed. Invalid/unrecognised destination files
  are rejected. Keep sufficient disk space for both old and staged output.
- Inputs, generated tiles, decoders, tools and local evidence are ignored by git.
  Recreate them using the commands in [README](../README.md).

## Deliberate limits

- Height-curve edits require an offline rebake. Wetness changes shading at runtime.
- The ±1 m water slider only moves existing baked water geometry. It cannot flood
  new land. Reservoirs are flat; each river follows its own mapped downhill profile, with
  wider-river priority at confluences. Native water membership controls bed lowering;
  clods are damped and dry banks supported near mapped shores.
- One warm directional light, baked AO, no real-time shadows, reflection/refraction
  passes, or desktop blur. Google 3D Tiles are not extracted or shipped.
- GPU figures estimate PlayCanvas allocations plus the default framebuffer;
  browser/driver overhead is not measurable through this counter.
- Local validation combines Khronos glTF validation, decoded bounds and implicit
  subtree checks. It is not a claim of complete OGC conformance certification.
- The photograph remains authoritative. Current renders need further judgement
  on rounded hand-made shape, granular irregularity and the smooth material split;
  passing functional tests does not establish a close visual match.

## Review

Claude `claude-fable-5-1` completed the requested read-only review after the quota
reset. Its complete report and the host's verification are in
[claude-review.md](claude-review.md). Confirmed water-bank, material-mask,
canal-width/name, lighting, retry and toolchain findings were corrected and rebaked.
Tests also reproduced and closed the native-bed-membership and tributary-profile
hypotheses. The ShaderMaterial clone hypothesis was disproved against pinned
PlayCanvas source. Follow-up review of the correction diff and new stills completed: no remaining
P1 technical blocker was confirmed. S1/S2 fidelity remains unmet; S4 shore facets
need cleanup, and discarded-water-pixel bank smoothing needs investigation. See
the full follow-up report for the next acceptance work.

[validation.md](validation.md) distinguishes final diagnostics from physical phone
qualification and documents the embedded browser's variable presentation rate.
The complete photograph match and the final two ticket acceptance gates remain open.

A concurrent session added ticket status notes and `ticket-commits.bundle`. They
are preserved. That bundle predates the review corrections; the current working
tree and this validation report contain newer implementation changes. No bundle
import or history replacement was performed in this review workflow.
