# Claude independent review

Workflow status: **DONE_WITH_CONCERNS**.

Model: `claude-fable-5-1`. Read-only CLI review of 67 files and six images,
including the source photograph, complete authored source, requirements, locks,
tests, generated metadata and local validation evidence. No tools were permitted
to the reviewer; it did not run tests or watch the video.

Snapshot SHA-256: `a91b046647eb17cfbd51ee25e00bafc71dcfca01f909f38dd2376140ba6519e7`.

## Original report (verbatim)

**Outcome:** no P0 code defect confirmed. Sign-off is blocked by the style gap (S1, S2, S3, S5 fail on the supplied renders), by the absence of any physical phone measurement, and by three P1 defects in how water and the material mask are derived. Everything below is from reading the source and the attached stills. I ran nothing and did not watch the clip.

## Findings by priority

**P1-1. Water planes ignore the ±60 m clod displacement on adjacent banks (confirmed mechanism, visual check needed).** `bake/water.py:114` computes river and lake levels from the clod-free source DEM, while `bake/shape.py:46` adds clods everywhere and nothing damps them near water. A valley river bank of a few metres becomes roughly 10 to 15 m after the remap, but the ground beside it swings ±60 m, so along much of the shoreline the land outside the polygon is below the water plane. Symptom: water reads as a raised cut-out laid over bumps instead of a sheet recessed between banks. The Sanchez and valley-fields stills show canals and the reservoir edge sitting on top of the lumps. Fix: in `prepare_water`, before the carve, blend `heights` toward the clod-free remapped DEM inside the existing `band` falloff, or multiply the clod term by one minus that band. Add a test that a bank within 100 m of water never lies below the water level.

**P1-2. The crust/granular mask is a saturated binary map of the clod noise (confirmed).** `bake/material.py:24` uses curvature×90. A 36 m clod at 170 m wavelength has curvature near 0.05 per metre, so the term is about 4.4 and clips hard: every clod top is crust, every clod pit is granular, independent of landform. All five renders show the resulting uniform leopard-spot pattern at one wavelength. The photograph's split follows the large hand-modelled masses, with crust on broad tops and dark on big steep faces. Fix: derive curvature and slope from the clod-free remapped DEM at a coarser sigma (200 to 400 m), cut the curvature weight by about ten, raise the slope weight, and leave small-scale breakup to the detail textures.

**P1-3. The canal network renders as a road grid (confirmed).** `bake/imagery.py:151` keeps every NHD CanalDitch feature and `bake/water.py:95` buffers each to 60 m total width in the same bright water colour. The valley-fields still shows a rectilinear white grid of laterals and drains, which is exactly the "mapped roads" read PRD item 7 and S5 forbid. Fix: keep only named main canals and acequias (or fcode 33600 with a GNIS name), drop names containing Drain or Lateral, reduce width to 15 to 20 m, and consider a dimmer tint for canals.

**P2-4. "Rio Grande" substring widens the Rio Grande Drain ditch to 360 m (confirmed).** `bake/water.py:95` tests substring containment and the manifest's named features include "Rio Grande Drain". Fix: match the exact name and require ftype 460 or 558.

**P2-5. Default and fixed views are backlit (confirmed from geometry).** The sun at `bake/material.py:12` sits to the north-west, and the default yaw at `src/orbit.ts:3` places the camera south-east looking north-west; every fixed view keeps that yaw. Camera-facing slopes are therefore in shadow, while the photograph is lit from over the camera's shoulder. This darkens every render and feeds the S3, S6 and S7 failures. Fix: rotate the default yaw by about π, or move the sun to the camera side. A sun change needs a rebake only for the small aspect term in the mask.

**P2-6. Micro-detail cannot be seen (confirmed by arithmetic).** Flecks are five texels in a 512-texel tile repeating every 1200 m (`src/shaders/terrain.frag:47`), so about 12 m across. The nearest allowed camera distance at `src/orbit.ts:28` is 3.4 km, where 12 m is one pixel at 1440p and the mip chain averages it away. S5 cannot be demonstrated as built. Fix: scale flecks to 60 to 120 m and strands to about 30 m, or permit closer zoom and sample with a negative mip bias.

**P2-7. A slow network permanently degrades tiles and shows developer text to visitors (confirmed logic).** `src/texture-load.ts:12` starts a 30 s timer when the request is queued, not when it starts. On a slow mobile connection with bursts of twenty-plus masks behind six parallel connections, later masks can exceed 30 s. `src/main.ts:120` then leaves the tile on the diagnostic StandardMaterial forever and displays "Run npm run setup:bake" to the visitor. Fix: no fixed timeout or one measured from fetch start, retry on failure, and a user-facing message.

**P2-8. Unverified download of code shipped to every visitor.** `scripts/setup_tools.py:36` fetches three Basis transcoder files from a GitHub tag with no checksum, while the KTX package on the previous lines is checksummed. Tags are mutable. Fix: pin sha256 digests or a commit hash, or copy the files from the installed playcanvas package.

**P2-9. Hypothesis: ShaderMaterial.clone may not copy parameters.** `src/main.ts:107` relies on the clone carrying uNormal, uSun and uExtent. If PlayCanvas copies only render state, the clones render correctly today only because the shared program's uniforms retain values from the shared material's last draw. If uExtent ever reads zero, all water turns the background colour. Fix: set every parameter explicitly on each clone. That is cheap and removes the dependency either way.

**P2-10. Hypothesis: lakes that rasterize to no 40 m cell get a distant river level.** `bake/water.py:108` rasterizes lakes without all_touched. A thin lake missing from the raster is skipped by the fill routine but still meshed from the vector union at the nearest-channel level (`bake/water.py:122`) and carved 20 m below that level at `bake/water.py:164`. Outcome is a floating disc or a deep pit. Fix: assign lake levels per vector polygon, and add a test with a 30 m wide lake.

**P2-11. Hypothesis: coarse-LOD bed lowering carves outside water polygons.** `bake/water.py:32` lowers any 40 m wet cell whose sample sits more than 10 m below the level. The wet raster is all_touched and up to one cell wider than the polygons, and the clod dips from P1-1 satisfy the 10 m test. At LOD 0 to 2 this digs pits of 184, 92 and 46 m just outside shorelines. The overview still shows dark fringes along rivers that are consistent with this. Fix: test membership against the native polygon raster rather than the 40 m mask.

**P2-12. Hypothesis: tributary levels bleed into main-river bank vertices.** `bake/water.py:112` picks the nearest channel cell regardless of width. A Rio Grande bank vertex is 180 m from its centreline and can be nearer a steep arroyo's core cells, whose level is tens of metres higher after remap. Expect water spikes at gorge confluences. Fix: normalise the nearest search by channel half-width, or assign levels per source feature.

**P3-13. Trace evidence is perturbed.** `scripts/check-browser.mjs:94` keeps a CDP screencast running and line 88 disables the cache during the 60 s trace. The 84 fps on an M3 Pro is itself about 12 ms per frame, which is unexplained (vsync, CPU in tile update, or capture overhead). Profile before assuming phone headroom.

**P3-14. Toolchain provenance.** `bake/material.py:75` prefers a PATH toktx over the pinned one, but `bake/__main__.py:104` records 4.4.2 regardless. `bake/__main__.py:116` runs the compressor by a CWD-relative path at the very end of a multi-hour bake with no preflight for node or toktx. Fix: resolve from `__file__`, record the real tool version, preflight both tools.

**P3-15. Imagery artefacts.** Invalid SCL cells get NDVI 0 and a dark tone of 0.40 (`bake/__main__.py:89`), and one scene per MGRS cell on different dates can leave tonal seams near local x ≈ +37 km and z ≈ +17 km. Amplitude is low. Inspect the valley floor.

**P3-16. The S7 swatch method is tautological.** `scripts/create-review-evidence.py:46` searches each region for the patch nearest the target colour, so it always matches. Use region means or histograms instead.

**P3-17. Minor.** The "tiles loaded" counter never decrements (`src/main.ts:124`). The load-error banner is developer-facing. tsc does not typecheck tests. `test_cli` uses a 10 s subprocess timeout that will flake on slow machines. `urlretrieve` has no timeout. The PRD names NAIP but only Sentinel-2 is used. `prepare_water` mutates the shaped heights in place, which feeds the preview grid and material fields, and no doc says so.

## Visual assessment of S1 to S7

The renders are a dark sepia relief with one periodic spot pattern. The photograph is mostly pale tan and beige, with dark confined to crevices and steep faces, and its land is only about a fifth darker than its water. In the renders the land is roughly half the water's brightness. The sampled water colour does match the reference and the earlier lavender guess is correctly abandoned.

- **S1, not met.** Bumps are uniform across valley floor and mountains alike. The Culebra view reads as a smoothed DEM with a popcorn overlay, not as stacked pinched lobes at ridge scale. Shorelines are sharp, but water sits on top of the land (P1-1).
- **S2, not met.** Both tones exist, but the split is the clod spot map (P1-2). Dark areas read as felt rather than pitted clasts, because 11 m clasts are sub-pixel at every permitted distance, and crust is not visibly smoother than granular.
- **S3, not met.** No pale veil is visible and upward flats are not paler. Saturation and darkness exceed the reference.
- **S4, partial.** Planar, matte, light and sharp-edged: yes. The rim is barely perceptible and grain is invisible. Because water is by far the brightest element, it reads as cut paper rather than painted plaster. Shimmer is unassessed here.
- **S5, not demonstrated.** No flecks or strands are visible in any still, and the canal grid produces the road-like lines the brief excludes.
- **S6, partial.** One warm sun, dark crevices and an oblique no-horizon camera are present. The backlit composition (P2-5) contradicts the photograph's lighting.
- **S7, inconclusive.** The patch samples match by construction (P3-16). Whole-image tonality is far darker and greyer than the reference.

The author's own note about smooth shapes and the material split is accurate. The bigger issue is that the split and the lumpiness come from the same 170 m noise, so fixing one without the other will not move the look toward the photograph.

## Open gates and what blocks sign-off

Still open: iPhone 12 trace, Snapdragon 7-series trace, cold-cache first view on a phone network, on-device LOD seam and touch checks, S1 to S7 sign-off, water clip review, and the villages/paths decision.

Sign-off is blocked by three things. First, the style gap: S1, S2, S3 and S5 fail now, and closing them needs P1-1, P1-2, P1-3, P2-5 and P2-6 followed by a rebake and new fixed-view captures. Second, no physical phone has been measured, and the desktop traces were captured with instrumentation running, so they say nothing about the budget. Third, the confirmed data and visitor-facing defects P2-4, P2-7 and P2-8 should be fixed before publishing. The hypotheses P2-9 through P2-12 each have a cheap fix and should be closed during the same rebake.

## Host verification and corrections

These are host findings, separate from Claude's original report above. A follow-up
review of the correction diff and four new stills completed successfully; its full
report is below.

| Finding | Verification / action |
|---|---|
| P1-1 Water banks | Reproduced negative-clod dry bank below water in a failing test. Damp clods near shores and support dry banks above the plane before native bed carving. Regression passes. |
| P1-2 Material split | Primary mask now uses clod-free landforms smoothed over 200 m, curvature weight 9 and slope weight 1.6. Regression confirms small clods cannot control the primary mask. Rebaked all masks. |
| P1-3 Canal grid | Omit unnamed canals, drains and laterals; retain named main canals/acequias at 20 m total width. 751 source canal features omitted from rendered water. |
| P2-4 Name match | Exact Rio Grande match plus stream/artificial-path type; regression rejects Rio Grande Drain widening. |
| P2-5 Backlighting | Moved sun to SE, on default camera side; source and runtime agree. Aspect and camera-side light regressions pass; full rebake. |
| P2-6 Detail visibility | Weak visibility accepted. The arithmetic in the report is incorrect: 12 m at 3.4 km / 1440 px / 38° vertical FOV projects to about 7.4 px, not one. Doubled mark atlas world scale and allowed closer constrained zoom; visual legibility still needs judgement. |
| P2-7 Loading | Removed default queue timeout, retry actual failures, retain optional explicit timeout cleanup, show delayed-load help without rejecting. Public Retry view action replaces developer instructions. Tests and real blocked-mask/recovery browser check pass. |
| P2-8 Decoder integrity | Pinned SHA-256 checks for all three Basis files, including existing files. Verified downloads cannot replace an existing file on checksum failure. |
| P2-9 Clone hypothesis | Disproved against PlayCanvas 2.24.0: ShaderMaterial.copy calls Material.copy, which copies every parameter's data. No redundant workaround added. |
| P2-10 Thin lakes | No original failure asserted. Connected vector outlines now share planes, rasterize all_touched, and extend level support under vector shores. 30 m wide lake regression passes. |
| P2-11 Bed membership | Reproduced lowering outside native geometry when only the coarse mask was wet. LOD bed lowering now checks native point-centre polygon membership. Regression passes. |
| P2-12 Confluences | Reproduced ~149 m level error near a wide main river / steep tributary fixture. Profiles now come from each reach's own centreline, wider reaches own overlaps. Regression passes. |
| P3-13 Measurement | Stop screencasting and restore normal caching before timing. Preserve slow runs and empty-canvas control as well as final fast runs. No phone or independent standalone-browser performance claim. See validation report. |
| P3-14 Toolchain | Preflight before reading DEM. Prefer verified local KTX, reject wrong version, record actual KTX/Node/glTF-transform versions, resolve compressor from repository source. Verified real full bake succeeds. |
| P3-15 Imagery | Invalid reflectance contributes no dark bias; valid-weighted blur falls back to neutral tone. Different-date mosaic seams remain an inspection item. |
| P3-16 Swatches | Fixed 40×40 region means and luminance percentiles replace target-colour search. No numeric fidelity pass is inferred. |
| P3-17 Minor items | Resident tile count decrements; public errors corrected; tsc checks tests; CLI test allowance 30 s; NHD downloads timeout; height mutation documented. Sentinel-2 is an allowed imagery alternative, and the human-feature decision was already settled: no actual villages or roads. |

Current verification: **36 Python tests + 8 TypeScript tests pass**, including
TypeScript checking of test files. Production build passes with the existing large
chunk warning. All **341 GLBs** pass decoded validation and local tile checks with
zero errors or warnings. [Validation evidence](validation.md) contains exact metrics
and distinguishes diagnostics from device qualification. S1–S7 approval and physical
phone gates are still open; these corrections are not a claim of final style sign-off.

## Claude follow-up (verbatim)

Correction snapshot SHA-256: `ebcbc376324e924e02fbf063f8e52f2cfc5c7985c547cdcc8ecc05b1945f21c6`.

**Bottom line:** the corrections close every confirmed code defect from the first report, and the new stills fix lighting, tonality and water seating. No remaining P1 technical blocker is confirmed. Two new P2 artefacts appeared, S2 still fails for a different reason, S1 remains open, and nothing qualifies a phone.

## Original findings: status

- **Closed (verified in diff):** P1-1 bank support and clod damping in `bake/water.py` near line 229; P1-3 and P2-4 via `channel_half_width`; P2-5 sun moved to the camera side with a regression test; P2-7 retry flow with visitor wording and a recorded blocked-mask recovery; P2-8 pinned digests through `download_verified`; P2-11 native membership in `lower_water_bed`; P2-12 per-reach profiles with wide-river priority; P3-13 screencast stopped before timing; P3-14 preflight and recorded tool versions; P3-15 weighted NDVI; P3-16 fixed-region means; P3-17 cumulative counter, tsc coverage, test timeout.
- **Closed by host investigation, accepted:** P2-9. The host checked the pinned engine source for parameter copying. I accept that.
- **Corrected against me:** P2-6. My one-pixel figure was wrong. At the old minimum distance a 12 m mark was about 7 px. The doubled atlas scale and closer zoom are reasonable; faint rust specks are now visible in the close still.
- **Partially closed:** P1-2. The split now comes from the clod-free landform, which removes the spot pattern. See S2 below for why it still misses.
- **Closed by mitigation, not by evidence:** P2-10. Connected outlines and all-touched lake masks plus the 30 m lake test cover the mechanism I described.

## New or remaining technical issues

- **P2, new, confirmed in stills: faceted shelves along shores.** The bank support step at `bake/water.py` near line 232 raises dry ground to the water plane plus 2 m, then the carve drops the bed 20 m. The TIN resolves that ledge with large triangles, so flat-shaded facets appear along the reservoir's south-east bank, around the detached ponds in the valley view, and under the ponds in the close view. Narrow fix: feather the support over 30 to 60 m instead of a step, or add a sample-dense ring to the TIN input near shores.
- **P2, hypothesis: stray NDWI pixels drive terrain smoothing.** The support and damping distances are measured from the 40 m `wet` raster, which includes detected pixels too small to become polygons. Each such pixel flattens and lifts a 280 m disc of land with no water in it. Check the valley floor for isolated smooth dimples.
- **P3: the material curvature term is now inert.** With a 200 m sigma and weight 9, real landform curvature after the remap contributes under 0.03, so the mask is effectively slope only. This is why the split reads as a smooth band.
- **P3: performance evidence is internally contradictory.** An empty clear at 20 fps and a full scene at a flat 120 fps in the same pane cannot both describe the renderer. The host's own conclusion is correct: diagnostic only. No phone has been measured and I do not certify one.

## S1 to S7 against the photograph

Overall the renders moved a long way in the right direction. Tone is now pale warm beige with water only slightly brighter than land, which matches the reference relationship. Lighting is front-lit. Water sits in recessed channels with visible banks.

- **S1, open.** Banks now pass: the reservoir and gorge reaches meet land with a sharp drop. Relief still fails: the surface reads as soft sand dunes or velvet, not stacked hand-pinched clods. The 60 m clods are visible only as gentle dimples and nothing at ridge scale is lumpy.
- **S2, fails, different cause.** Dark material is confined to steep faces as a smooth airbrushed gradient. The criterion requires a broken, clumpy boundary and visible pits. The granular texture reads as fur or felt at every supplied distance, and crust is not visibly smoother than granular. This is the largest remaining gap.
- **S3, close to passing.** A pale veil is now present and dominant. It may be slightly too uniform, with little difference between upward flats and slopes.
- **S4, partial.** Planar, matte, warm, sharp contact and a visible rim: yes. Grain still invisible. The new facets at some shores break the clean contact line. Shimmer unassessed.
- **S5, weak pass at close range.** Sparse rust specks are visible in the close still. Pale strands are not evident. The remaining named-canal rectangles on the valley floor still read as drawn lines rather than channels.
- **S6, pass on lighting and view.** Front-lit warm sun, oblique camera, no horizon. Crevice darkening is now rather mild and could be strengthened.
- **S7, plausible but unverified.** The family of tones is right. The reference's saturated ochre and dark pitted brown are both underrepresented, so a side-by-side swatch sheet with the new fixed-region method is still needed.

## What still blocks sign-off

S1 and S2 are not met and need a morphology and texture pass, not a parameter tweak: larger-scale lumpiness tied to ridges, a clumpy material boundary, and coarser granular clasts. The shore facets need fixing before S4 can pass. Physical iPhone 12 and Snapdragon 7-series traces remain entirely open, and the water clip has not been reviewed.

## Current acceptance boundary

The host does not claim final reference fidelity. The next visual slice must address
S1 ridge-scale sculpted lobes and S2 broken clumpy material boundaries / readable
pitted clasts. S4 shore facets are a confirmed follow-up issue. The proposed
discarded-water-pixel smoothing mechanism remains a hypothesis to test against
canonical surviving polygons. Fixing shores must preserve dry-bank support and
streaming budgets. These remain open alongside physical phone measurements and
watching the water clip. No additional village/road decision is needed: that
feature policy was already settled.
