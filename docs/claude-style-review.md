# Claude review: visual style PRD and reference patch plan

Status: **DONE_WITH_CONCERNS**, re-review **Ready to start**. Claude initially reviewed commit
`ad7815403f2434604a676fc01099b1979fade8fc`. Its original verdict was **not ready to start**.
Claude subsequently re-reviewed the corrections at `ab760e2` in the same session
and closed all five original P1 blockers. It returned **Ready to start**, with seven
P2 task-level refinements. Those refinements are incorporated below; no third review
is claimed. No terrain implementation or visual acceptance was performed here.

Model: `claude-fable-5-1`. Session: `010edd1d-0c18-41d0-b890-668f671b61e6`.
Scope: PRD, implementation plan, relevant existing bake/material/shader source and
installed PlayCanvas POM code; original photograph, five generated studies and two
rejected current renders. All tools disabled for the nested review. Raw request,
response and scope snapshot remain locally in ignored `data/claude-style-review/`.
Claude did not execute tests or watch animation clips.

## Host verification and disposition

Numbers below correspond to Claude's findings, preserved verbatim afterwards.

| Finding | Disposition |
|---|---|
| 1 Scale | Added initial scale table, camera framing and feature metadata. These are tunable art targets, not measurements recovered from images. |
| 2 Portable composition | Added explicit unique-UV compositing into standard PBR atlases: sixteen 500 m cells at 2K initially, measured surface texel density and optional 4K. Authoring triplanar is baked; preview-only experiments cannot satisfy portability gates. |
| 3 Recipe constraints | Added named occupancy, shape, size-distribution, cavity, sidewall and directional parameters. Replaced the suggested multimodal-neighbour test with a spread calibration: natural clustered distributions can be unimodal. Visual approval still required. |
| 4 Circular gates | Task 2 owns a minimal Blender source renderer; VS2 can close on Blender geometry renders. Task 5 creates capture tooling before Task 6 uses it. |
| 5 Portability loophole | V1/V2/V4 now must pass on a fresh standard-GLB Blender import without POM at the close camera. |
| 6 Height conversion | Added physical-to-UV conversion and calibration, plus a correction to Claude's public-property formula: installed PlayCanvas `convertHeightMapFactor` multiplies by 0.1, so the public property needs `10*range/span` for the planar fixture. Packed UVs require their actual surface metric. |
| 7 Normal convention | Verified RGB tangent convention and upper-left UV origin against the glTF specification. Added exported tangent conventions and two-light cross-consumer calibration; avoided treating arbitrary UV islands as world-north aligned. |
| 8 Diagnostic light | Added azimuth/elevation controls in Task 5. |
| 9 Linear pipeline | Added explicit colour/data texture handling, exposure and tone-map settings with capture metadata. |
| 10 Residual tests | Replaced vague amplitude assertion with neutral full-detail and analytic master-minus-receiver normal fixture tolerances. |
| 11 Patch suitability | Remains a source-inspection decision, not a confirmed site defect. Task 1 must demonstrate bank plus tributary ridge relief before locking the site; includes Culebra foothill candidate. |
| 12 LOD order | Pre-approval LOD work is fixture-only; production derivation follows visual approval. |
| 13 Height precision | Added float runtime comparison baseline and explicit upload verification. Neither 16-bit PNG storage nor a fixed POM sample count guarantees absence/presence of stepping; variants need visual comparison. |
| 14 Shore/amplitude integration | Named shader-extension requirement in PRD and Task 5. |
| 15 Roughness | Added initial clay/aggregate/worn-face ranges and retained filtered LOD roughness requirements. |
| 16 Baked lighting portability | Direct-light bakes are labelled reference/optional output; standard baseline remains relightable with separate AO. |
| 17 Fixtures | Task 1 numerical tests explicitly use synthetic rasters, independent of cached GIS inputs. |
| 18 CPU/shader verification | Retained shader counterpart captures and two-light fixture checks; TypeScript tests alone do not prove GLSL correctness. |

The five initial P1 documentation gaps have concrete revisions. Asset scale,
clustering, atlas density, POM quality and site suitability are still hypotheses
until the patch is built and compared. User visual approval remains the gate.
Documentation validation covers links, placeholders and dependency ordering only;
it does not validate shader maths, generated assets or a rendered look.

## Verification sources

- Installed `node_modules/playcanvas/build/playcanvas/src/scene/materials/standard-material.js`, `convertHeightMapFactor` (multiplies public factor by 0.1).
- Installed `scene/shader-lib/glsl/chunks/standard/frag/parallax.js` (normalised height/base and UV-depth usage).
- [glTF material normal convention](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materialnormaltextureinfo) and texture-coordinate origin.

## Original Claude response (verbatim)

**Visual gap read**

The references share four traits the rejected captures lack: mound-scale pinched ridges with lobed, chipped crests; dark aggregate as clustered, cavity-separated clods confined to slopes and bases, not spread evenly; worn ochre faces with fall-line striations and wet-looking specular; pale channels that are smeared flat floors between supported banks. The rejected close view shows inflated dunes, a single evenly packed Voronoi dot pattern (the `detail_textures` cells in `bake/material.py:41-49`), bright white water strips and vertical carved shelves. The gap is geometry and distribution first, maps second. The PRD diagnoses this correctly, and the three-band separation in `docs/visual-style-prd.md:179-181` is the right structure. The plan, however, leaves the pieces that determine whether the result is clods or new wallpaper unspecified.

## P1: block implementation until fixed

1. **No declared miniature scale.** `docs/visual-style-prd.md:94` (V7) and `:247` require "coherent clod sizes" and "match reference apparent feature scale", but nothing states what a clast, a cluster, a ridge fold or the close camera distance is in metres. `span_m` in the manifest (`plan:52`) has no target. Without this, Task 2's recipe, the 2K-vs-4K decision (`prd:126`), the close camera (`plan:68`) and every V7 judgement are unanchored. Fix: add a scale table to PRD section 5.4 (for example clast 8–40 m, cluster footprint 60–300 m, fold wavelength 150–600 m, close camera 1.5–3 km from target) and record it in `configs/style-materials.json` and the manifest as `feature_scale_m`.

2. **Portable material composition path is undefined.** Task 2 (`plan:83`) authors two tiling exemplars. Task 3 (`plan:97`) bakes residual detail on the receiving surface. glTF allows one texture set per primitive, so blending clay and granular exemplars by ID mask cannot exist in the "standard GLB" unless a per-patch unique UV atlas is baked. No step performs that composite, and `prd:153-154` still permits triplanar, which glTF and Blender cannot express. Fix: declare that the portable GLB uses unique per-patch UVs with a composited atlas (exemplars composited by `maps.py` or Blender), and that triplanar is preview-only and may not be used for any V-criterion evidence. State the atlas texel density this implies for a 2 km patch.

3. **Procedural recipe has no constraints that exclude the previous failure.** `plan:82` says "deterministic spatial cells, varied shapes, empty spaces, sparse fragments". That describes `material.py` today. Missing: cluster occupancy driven by slope, aspect and curvature; log-normal size distribution; occupancy fraction inside clusters versus bare clay; minimum gap depth relative to clast radius; sidewall slope; striation direction along the fall line; a rejection test for spatial periodicity or uniform cell spacing. Fix: enumerate these as named recipe parameters with reference-derived ranges in `configs/style-materials.json`, and add a test asserting the nearest-neighbour distance distribution is not single-peaked. Tests still do not grant visual acceptance, but they stop the obvious regression.

4. **Circular gates in Task 2, 6 and VS2.** `plan:84` requires a Blender neutral preview that only exists after `blender_bake.py` (Task 3). `prd:235` requires VS2 shown "in the viewer", which is Task 5. `plan:135` and `:144` require a capture script and 10-second clip created in Task 7. Fix: move a minimal Blender render entry point into Task 2, let VS2 close on Blender renders, and move `scripts/check-style-study.mjs` into Task 5.

5. **Portability gate is a loophole.** `prd:60-61` and `:238` require only that the GLB "retains material identity" in Blender, while POM is optional. If the approved look depends on POM, the standard package will look like the rejected build. Fix: VS5 requires V1, V2 and V4 to pass on the Blender standard-material render at the close camera, not only "identity".

## P2: resolve before the relevant task

6. **Height convention not mapped to the engine.** `parallax.js:21,39` treat texture value 1 as the top surface, with `material_heightMapBase` as the fraction where geometry sits, and `material_heightMapFactor` in UV units. The manifest carries `height_zero` and `height_range_m` in metres (`plan:52`). Specify the conversion: factor = height_range_m / span_m, base = (geometry_height − height_min) / range. Recommend base near 1.0 so POM only carves between clasts and never lifts relief above the real silhouette, consistent with `plan:18`.

7. **Normal convention needs glTF wording.** `opengl-positive-y` plus "rows increase south" (`plan:78`) is ambiguous. State per glTF: green points to the top of the image, so green = north for a north-first raster, with v = 0 at row 0. Note the existing `write_glb` (`bake/tile.py:53`) builds v increasing southward, which matches. The Python ramp tests (`plan:81`) only verify Python against itself; the Task 3 raised-clast fixture is the real check and must be run under at least two light azimuths.

8. **Diagnostic light missing.** `prd:147` requires a rotating diagnostic light. Task 5 controls (`plan:124`) list debug channels but no light azimuth/elevation control. Add it.

9. **Linear pipeline step missing.** `prd:149` mandates a documented linear-light pipeline, replacing the `sqrt` at `src/shaders/terrain.frag:43`. No task sets sRGB flags on base colour, linear on data maps, exposure and tone mapping. Add to Task 5 and record in capture manifests.

10. **Residual-normal test is not implementable as written.** `plan:111` "no duplicate full-amplitude displacement" has no measurable definition. Replace with: residual map on the full-detail level is neutral within tolerance for all features above the geometric threshold, and the mean residual-normal tilt equals the master-minus-LOD slope on a synthetic ridge fixture.

11. **Patch choice versus composition target.** `plan:67` picks a Rio Grande gorge reach. That is a flat basalt plateau with a single slot: good for reference 04 banks, poor for ridge lobes and the V1 silhouette test. Hypothesis, not defect, but choose a reach that also contains a tributary ridge system (Culebra foothills), or add a second labelled patch.

12. **Task 4 ordering.** Deriving LODs before any visual acceptance (`plan:112` "from the accepted source") means rework. Keep Task 4 as a throwaway continuity proof on fixtures and derive real LODs after VS5.

## P3: resolve during patch iteration

13. **Runtime height precision.** Height masters are 16-bit (`prd:125`), but KTX2/UASTC storage yields 8-bit, which produces stepped POM at 16 samples close up. Keep an uncompressed or 16-bit runtime height texture for the comparison.

14. **Per-region amplitude and water fade.** `parallax.js` fades only by march texels (`:29`) with one scalar factor; shoreline fade and per-material amplitude need a chunk override. The plan acknowledges extensions (`plan:127`) but should name this as the trigger.

15. **Roughness underspecified.** References 02 and 05 show wet specular on ochre faces versus matte aggregate. Record roughness ranges per material and use normal-variance-to-roughness when downsampling (`plan:112`).

16. **Offline baked lighting is not portable.** `prd:189-190` comparison is fine as a reference render, but glTF carries only AO. Label it as reference-only in Task 6.

17. **Test fixtures.** Task 1 tests need synthetic rasters; they must not depend on the cached DEM.

18. **TS normal helper.** `plan:126` tests a TypeScript mirror, not the GLSL. Keep it, but the raised-clast screenshot is the actual verification.

## Consistency checks that pass

PlayCanvas 2.24.0 claims in `prd:159` are confirmed in `parallax.js:3,36,74`. The grazing clamp (`parallaxMaxSlope`, `:19-20`) addresses the top listed risk. StandardMaterial applies one `dUvOffset` to all maps, matching `plan:128`. Axes `x-east,y-up,z-south` match `bake/tile.py:101-105`. The staged publisher in `bake/output.py:13` has an allowlist the plan correctly does not extend.

## Recommended changes before starting

1. Add the scale table and feature-scale metadata (P1.1).
2. Decide: unique per-patch atlas for the portable GLB; triplanar preview-only (P1.2).
3. Enumerate recipe constraints and a periodicity rejection test (P1.3).
4. Reorder: minimal Blender render in Task 2, capture script in Task 5 (P1.4).
5. Strengthen VS5 to require V1/V2/V4 on the Blender render (P1.5).
6. Write the height and normal convention conversions into the manifest schema section (P2.6, P2.7).

**Verdict:** Not ready to start. The direction and technique stack are correct and should close the gap if the sculpted band is real geometry with constrained clustering. As written, the plan can be executed to completion while producing a second generic surface, because scale, composition path and recipe constraints are unspecified and three gates reference tooling built later. The six changes above are documentation edits of about a day. Once in, Tasks 1 through 3 can proceed; Tasks 4 to 7 need the P2 items first.


## Re-review of ab760e2

Claude re-reviewed the complete corrected PRD and plan, correction diff and installed
engine height-factor conversion evidence, retaining the earlier references in its
session context. The original five blockers were closed. Its exact verdict was
**Ready to start**; Task 1 can begin, with refinements before their owning tasks.

### Host disposition of remaining P2 findings

1. Added `clast_instances` records with positions, radii, orientation, shape and stable
   ids in Task 2; its source renderer builds simple geometry before Task 3 refines it.
2. Task 3 checks V1/V2 and clast contact; full bank/channel V4 follows integration
   and remains required at Task 7.
3. Added explicit north-rising/green-below-neutral and reverse-ramp assertions.
4. Added VEC4 tangent/accessor, unit-length and handedness checks to export tests.
5. Added per-island UV-to-surface metric metadata/calibration for POM; planar scalar
   fallback is restricted to verified uniform planar islands.
6. Bank checks now refer to the full-quality patch plus fixture LODs before VS5.
7. Added bounds-based per-cell visibility loading, a prefetch ring, lazy comparison
   variants and GPU resource release to the preview adapter contract.

These are documentation changes, not implemented/tested runtime guarantees.
The review's claim that a coefficient-of-variation threshold cannot admit a jittered
lattice is too strong: sufficient jitter can pass. The test is a calibration against
regular grids, and explicit cluster occupancy plus image review still establish the
spatial character. No statistical test here guarantees a reference match.

### Re-review response (verbatim)

**Disposition of the original P1 blockers**

1. **Scale.** Closed. `docs/visual-style-prd.md:224-242` and `plan:99` fix the ranges, and `feature_scale_m` is in the manifest (`plan:52`). The numbers are internally consistent: at 1200 m and 40° vertical FOV a 1080-pixel frame covers about 870 m, so an 8–40 m clast is 10–50 px and 0.244 m texels give roughly three texels per pixel. Whether the look is right is the experiment, not a spec gap.

2. **Portable composition.** Closed. `prd:66-77` and `plan:55-59,114` define unique-UV atlases with the blend baked in, triplanar as authoring or labelled experiment only. See P2 item 7 for one memory consequence.

3. **Recipe constraints.** Closed. Named parameters at `prd:232-242`, stored and reported in `plan:99`. The nearest-neighbour coefficient of variation above 0.3 is a sound grid rejector: a perfect grid scores 0 and a Poisson scatter about 0.52, so the test cannot pass on a jittered lattice while leaving natural distributions alone. I accept the host's point that a multimodal test was wrong.

4. **Circular gates.** Closed. `blender_preview.py` is created in Task 2 (`plan:91,101`), VS2 closes on Blender renders (`prd:300`), and the capture script moves to Task 5 (`plan:136,147`) with Tasks 6 and 7 reusing it (`plan:154,168`). One residual dependency ambiguity remains, see P2 item 1.

5. **Portability loophole.** Closed. `prd:303`, `plan:59,116,171` require V1/V2/V4 on a fresh Blender import of the standard GLB without POM. One sequencing defect follows from this, see P2 item 2.

**Convention correctness**

The height mapping is correct against the installed shader. Normalised height 1 at the top matches `surfaceDepth = 1 - h` at `parallax.js:39`; `uv_depth = height_range_m / span_m` is the factor the shader expects in UV units for a square planar material; base 1 gives `geomDepth = 0` at `parallax.js:21`, so the march starts at the geometric surface and only carves. With the host's `convertHeightMapFactor` evidence (line 44-46), the public property as `10 * uv_depth` is right. The `vec2(x, -y)` flip at `parallax.js:15` is consistent with the stated upper-left image origin. The normal convention text at `prd:170-176` is the glTF convention and the residual-map tolerances at `plan:128` are measurable.

**Remaining P2 findings**

1. **Task 2 cannot show V4 without clast instances.** `plan:101` says the preview renders "authored surfaces/cluster meshes", but cluster meshes are first built in Task 3 (`plan:114`), and `sculpt_field` (`plan:94`) returns only fields. The VS2 gate (`prd:300`) includes V4 floating-deposit checks. Fix: add a `clast_instances` output to the Task 2 interface (position, radii, orientation, shape id) that `blender_preview.py` instances as simple geometry. Resolve before starting Task 2; it is an interface addition, not a redesign.

2. **Task 3 requires V4 before bank work exists.** `plan:116` demands V1/V2/V4 at the close camera in Task 3, but V4's bank-to-channel continuity (`prd:104`) is Task 6 work (`plan:161`). As written Task 3 cannot close. Fix: Task 3 requires V1/V2 plus the clast-contact half of V4; full V4 on the Blender import is checked in Task 7 (`plan:171`), which already says so.

3. **Normal sign test must be explicit, because the legacy code is inverted.** `bake/material.py:58-59` sets normal Y to minus the southward gradient, which under an upper-left origin is the opposite of glTF. The new `normal_from_height` tests (`plan:98`) should state the sign: a ramp rising toward image top (north) yields green below 0.5. Without this the "analytic ramp" test can be written to agree with the old code and pass.

4. **Validator should require exported tangents.** `prd:173` mandates MikkTSpace tangents so Blender and PlayCanvas do not derive different frames, but `scripts/validate-style-package.mjs` (`plan:111`) does not list a `TANGENT` accessor check. Add it. Task-level fix.

5. **POM metric on repacked islands.** `prd:201-202` correctly limits the planar formula, but `prd:75-76` says to subdivide/repack steep faces, which produces exactly the islands where the planar scalar is invalid. The preview adapter needs either per-island UV-to-surface scale stored in the package or a planar-projection-only atlas with accepted stretch. Decide at Task 3 with the fixture; not blocking.

6. **"Across all LODs" in Task 6.** `plan:160` tests bank contact across all LODs, but before VS5 only Task 4 fixture levels and the full patch exist (`prd:293-295`). Reword to "full patch plus fixture levels". Trivial.

7. **Preview GPU residency.** Sixteen 2048² cells with three RGBA8 maps plus mips and a float height texture come to roughly 1.3 GB resident, quadrupling where cells go to 4096². `prd:328-330` already requires recording residency and allows intervention only if review stalls. Add a per-cell visibility load to the Task 5 adapter interface so the comparison does not exhaust a browser context. Not blocking.

**Items checked and not raised**

The nested diagnostic light, linear pipeline, float height upload, fixture-only LOD ordering, synthetic test rasters, reference-only direct-light bakes and roughness ranges are all present with concrete task steps. Site suitability remains correctly a Task 1 inspection outcome (`plan:84`) rather than a resolved claim. No remaining circular dependency exists after the Task 2 instance fix.

**Readiness verdict**

Ready to start. All five original blockers are closed with concrete, consistent text, and the height, normal and residual conventions are correct against the installed engine and the glTF specification. Task 1 can begin unchanged. Before Task 2 begins, add the clast-instance output (P2.1) and the explicit normal-sign assertion (P2.3). Before Task 3 begins, split the V4 requirement (P2.2) and add the tangent check (P2.4). Items 5 through 7 are task-level decisions resolved with the prescribed fixtures and captures. None of the remaining findings is an implementation-blocking specification defect.
