# Sculpted Reference Patch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one visually convincing, portable San Luis terrain patch with sculpted clasts, coherent normal/height maps and a depth-technique comparison.

**Architecture:** Python builds deterministic source surfaces and portable asset packages; Blender supplies high-detail material baking and independent import verification. Standard glTF/PBR maps carry the baseline look. A separate PlayCanvas preview compares normal-only, POM and geometry variants; no engine imports or shader uniforms appear in the authoring contract. Derive matched geometry/material LODs only after the high-detail patch exists.

**Tech Stack:** Existing Python 3.12, NumPy/SciPy/rasterio, pydelatin, Blender CLI, glTF 2.0; existing TypeScript/PlayCanvas 2.24.0 for preview only.

**Spec:** [Visual style PRD](../../visual-style-prd.md), including engine-agnostic assets and section 5.5 LOD policy.

## Global Constraints

- Visual quality first, performance second; preserve high-detail masters.
- San Luis major geography remains recognisable; invented exemplar geometry is separately labelled.
- Standard GLB/PBR maps plus height masters are the core output; 3D Tiles/KTX2/meshopt are optional delivery derivatives.
- Geometry defines silhouettes and water contact; POM supplies apparent interior relief.
- No full-region rebake until VS5 visual approval. No physical-phone performance claims from desktop captures.
- This plan covers VS1–VS5 and a small LOD continuity proof. VS6 regional rollout and VS7 optimisation receive later plans based on the approved patch.

## Review Focus

1. Axis and normal conventions: raised calibration features must shade as raised in Blender and PlayCanvas (Tasks 2, 3).
2. Shared coordinate edges: cropped displacement, exported normals and derived LODs must not open seams (Tasks 1, 4).
3. POM at steep angles and shores: detail must not swim, cross water or escape an atlas (Task 5).
4. Portable fallback: standard GLB/maps must retain clump identity without custom shaders (Tasks 3, 6).
5. Source-data failure or bake interruption: existing terrain stays intact and input errors fail before publication (Tasks 1, 3).

## File boundaries and output contract

New modules live in `bake/style/`; existing regional commands remain usable.

- `patch.py`: window a georeferenced DEM and explicit mapped-water inputs.
- `surface.py`: deterministic sculpted height/cluster fields in global coordinates.
- `maps.py`: coherent material maps and their conventions.
- `package.py`: versioned manifests and engine-neutral source publication.
- `blender_bake.py`: Blender-only authoring/export entry point.
- `lod.py`: derive mesh/residual-map detail bands from the approved master.
- `__main__.py`: patch CLI orchestration; delegates to modules above.
- `src/style-study/`: preview adapter, controls, material integration and depth comparison.
- `scripts/check-style-study.mjs`: fixed-pose captures and orbit evidence, separate from regional benchmark script.

Package version `1` contains `manifest.json`, `source/`, `meshes/`, `textures/`,
`height/` and `review/`. Source masters are editable recipes and Blender geometry;
standard inspection meshes embed image textures in GLB. Height masters are float
EXR or linear 16-bit PNG with explicit zero/range. Manifest paths are relative.

`manifest.json` records `schema_version`, `units: "m"`, `axes: "x-east,y-up,z-south"`,
`source_crs`, `origin_utm_m`, `bounds_m`, `source_hashes`, `recipe`, `materials`,
`lods`, `water`, `cameras`, and `artistic_departures`. Each material records map paths,
`normal_convention: "opengl-positive-y"`, `span_m`, `height_zero` and `height_range_m`.
Each LOD records mesh path, geometric error in metres, texture dimensions and parent.
Do not make POM support a package requirement or embed engine objects in this schema.

## Task 1: Reproducible real patch and portable package shell (VS1)

**Files:** Create `bake/style/{__init__,patch,package,__main__}.py`, `configs/style-patch.json`, `tests/test_style_patch.py`; modify `.gitignore`, `package.json`, `README.md`.

**Interfaces:**
- `read_patch(dem_path: Path, center_utm: tuple[float,float], size_m: float) -> tuple[np.ndarray, dict]`: retain source spacing/CRS; require full coverage and finite samples.
- `write_package(stage: Path, metadata: dict) -> None`: validate schema and relative paths; write the manifest only after all referenced files exist.
- CLI: `uv run python -m bake.style --config configs/style-patch.json --output data/style-patch`.

- [ ] Add tests `test_patch_preserves_north_east_and_global_origin`, `test_patch_rejects_missing_coverage`, `test_manifest_rejects_escape_paths`, `test_failed_bake_preserves_previous_package`. Assert known planar sample heights/origin, rejection of nodata and `../` paths, and identical previous file hashes after injected failure. Watch these fail before implementation.
- [ ] Implement the interfaces using rasterio windows and a package-specific staged publisher. Do not extend the regional output allowlist to accommodate unrelated formats.
- [ ] Inspect the cached full DEM and mapped channels to select a 2 km patch around a real Rio Grande gorge reach with a steep bank. Commit exact UTM coordinates and source hashes in config; verify source overlay before locking them. Do not require a network download when cached inputs are present. Missing inputs produce an actionable CLI error.
- [ ] Write three explicit camera poses (elevated, overhead, close), source overlay and existing-look baseline into `review/`. Water inputs are clipped real geometry, with the source/version recorded.
- [ ] Run `uv run pytest tests/test_style_patch.py -v`, then the patch CLI and inspect manifest/source overlay. Add `npm run bake:patch` for that CLI; ignore generated output, retain config/recipe sources.
- [ ] Commit `feat: add reproducible engine-neutral terrain patch`.

## Task 2: Sculpted morphology and coherent material masters (VS2)

**Files:** Create `bake/style/surface.py`, `bake/style/maps.py`, `configs/style-materials.json`, `tests/test_style_surface.py`, `tests/test_style_maps.py`.

**Interfaces:**
- `sculpt_field(east: np.ndarray, north: np.ndarray, source: np.ndarray, recipe: dict) -> dict[str,np.ndarray]`: return height, crust weight, cluster weight, dust and cavity fields with documented units.
- `normal_from_height(height: np.ndarray, spacing_m: float) -> np.ndarray`: return unit tangent normals with explicit positive-Y convention; source rows increase south.
- `author_material(recipe: dict, resolution: int) -> dict[str,np.ndarray]`: return co-registered base colour, normal, height, roughness, AO and ID fields.

- [ ] Write failing tests for constant-height neutral normals, analytic ramps with known normal direction, crop-versus-global field equality and same-seed repeatability. Assert finite values, normal lengths within `1e-5`, and physically declared height ranges. The crop test must use nonzero world offsets.
- [ ] Implement global-coordinate cluster placement with deterministic spatial cells, varied ellipsoid/irregular clast shapes, empty spaces and sparse fragments. Shape major ridges with directional folds/chipped crests tied to source curvature and slope; replace uniform rounded noise as the style recipe. Do not convert photographed brightness into height.
- [ ] Define separate clay and granular masters at 2048², with 4096² optional. Produce all maps from the same sculpted height/cluster source; preserve linear height data. Include worn clay folds and sparse scratches, dusty cavities, varied clast packing and broken transition masks.
- [ ] Run targeted tests and generate a neutral clay preview through Blender (Task 3 connects it to portable GLB). Inspect top, side and oblique source renders against reference 04. Adjust the recipe based on actual silhouettes and clustered depth; record changes instead of treating tests as visual acceptance.
- [ ] Commit `feat: author sculpted clay and granular material masters`.

## Task 3: High-detail asset bake and portable glTF export (VS2–VS3)

**Files:** Create `bake/style/blender_bake.py`, `tests/test_style_export.py`, `scripts/validate-style-package.mjs`; modify package orchestration and README.

**Interfaces:**
- `blender --background --python bake/style/blender_bake.py -- --package PATH --action bake|verify`.
- Bake consumes only the package config/maps/geometry, creates high-detail source `.blend`, simplified GLB with standard material textures, and map-bake metadata. Verify starts a fresh Blender scene and imports the exported GLB only.
- `node scripts/validate-style-package.mjs PATH`: validates manifest/map references and GLB standard material bindings, axes, units, normals and bounds using existing glTF tooling.

- [ ] Add failing export integration tests for normalTexture/occlusionTexture/baseColor/roughness bindings, no PlayCanvas-only required extensions, and containment of all mesh vertices in recorded bounds. Include one raised-clast calibration fixture and one embedded-bank fixture.
- [ ] Implement actual cluster meshes for prominent clasts/loose fragments and terrain displacement for ridge folds/banks. Bake smaller residual detail against the simplified receiving surface, with tangent basis and normal orientation recorded. Keep AO separate from direct light; metallic remains zero.
- [ ] Export an uncompressed standard GLB with ordinary embedded textures plus external linear height masters. Preserve the editable source geometry/recipe. Require a working Blender executable with a clear preflight error before replacing prior output.
- [ ] Verify via fresh Blender import of the GLB, not the authoring scene. Render matching neutral, side-lit and final-lit views. Independently validate through Khronos glTF validation and the package checker.
- [ ] Run `uv run pytest tests/test_style_export.py -v` and `node scripts/validate-style-package.mjs data/style-patch`; inspect the imported render for correct raised/recessed relief and V1/V2.
- [ ] Commit `feat: bake portable sculpted terrain and PBR maps`.

## Task 4: Geometry and material LOD continuity proof (VS3)

**Files:** Create `bake/style/lod.py`, `tests/test_style_lod.py`; modify package exporter.

**Interfaces:**
- `derive_lods(master_path: Path, recipe: dict, output: Path) -> list[dict]`: generate close/mid/far representations and record measured geometric errors, residual-map paths, texture dimensions and parent references.
- All levels use the same package axes, origin, material physical spans and camera definitions.

- [ ] Add failing tests that simplification retains explicitly tagged shoreline/boundary vertices, each reported error encloses measured source-to-LOD deviation, and a package with two neighbouring sample patches has identical boundary positions. Assert no duplicate full-amplitude displacement in residual normals.
- [ ] Derive levels from the accepted high-detail source, preserving ridge/shore constraints; bake removed clast relief into each receiving mesh's residual normals/AO. Downsample material maps with normal re-normalisation and roughness treatment sufficient to avoid bright sparkling.
- [ ] Store selection guidance by projected geometric error and texel footprint. Keep the highest-detail source unchanged; do not hardcode phone budgets or PlayCanvas error settings into the asset generator.
- [ ] Run targeted tests, compare all levels in Blender at matching framing, and save a seam/transition evidence sheet. Runtime transitions are verified in Task 5.
- [ ] Commit `feat: derive matched terrain geometry and material LODs`.

## Task 5: PlayCanvas comparison adapter (VS3)

**Files:** Create `style-study.html`, `src/style-study/{main,package,materials,controls}.ts`, `src/style-study/parallax.frag`; create `tests/style-package.test.ts`, `tests/style-normal.test.ts`; modify Vite build inputs only as needed.

**Interfaces:**
- Open `/style-study.html?package=/data/style-patch/manifest.json` in development; accept a user-configured same-origin package URL for other hosting layouts.
- `loadStylePackage(url: string): Promise<StylePackage>` uses schema v1 without tile-path inference.
- Preview modes: standard PBR; corrected normal-only; POM 16/32 samples; POM with self-shadow; high-detail geometry reference. Debug channels: clay, normals, height, AO, roughness, final. Saved camera poses come from package metadata.

- [ ] Add failing tests for corrupt/missing manifest fields and root-relative/parent-path escape rejection. Add analytic normal calibration tests for neutral normals, rotated UV samples and blended detail against known reference vectors. Keep the numerical helper used by production and tests identical; browser screenshots verify its shader counterpart.
- [ ] Load standard GLB/materials directly for the portable baseline. Adapt PlayCanvas StandardMaterial parallax with narrowly scoped shader extensions where needed. If multiple material projection cannot be implemented correctly there, document the reason and implement the custom path against the same calibration assets; do not quietly duplicate the authoring model in the viewer.
- [ ] Implement consistent tangent frames and normal reorientation/composition. In POM modes, offset all matching material maps by the same hit coordinates. Use manifest height zero/range; clamp/fade grazing relief and fade at discontinuities and real water contacts. Provide unambiguous status for missing height capability.
- [ ] Add explicit LOD selection for inspection and footprint-based automatic selection. Coordinate geometry, map resolution and parallax complexity; show active asset level in diagnostics. Keep the existing regional viewer intact.
- [ ] Verify no floating detail, atlas bleeding, inverted bumps, UV swimming or shoreline overlap in all three poses and an orbit. Capture normal-only/POM/self-shadow/geometry comparisons from identical cameras. If POM adds artifacts, retain it as a labelled comparison until corrected.
- [ ] Run TypeScript tests and `npm run build`; save captures and commit `feat: preview portable terrain depth techniques`.

## Task 6: Integrated lighting, banks and silty water (VS4)

**Files:** Modify package recipe, Blender bake and preview materials; create `tests/test_style_shore.py` and extend the evidence script from Task 7.

**Interfaces:**
- Mapped water is a standard opaque pale material/mesh in portable export. Optional preview motion parameters are described in manifest water metadata (subtle normal scroll/glint), not engine-specific uniform names.
- Fixed key/fill and exposure are review-scene settings; source base colour remains unlit.

- [ ] Add a failing numerical bank-contact fixture test: terrain supports dry banks above the mapped water plane and bed below it across all LODs, with continuous shoreline vertices. Validate both a channel and lake edge.
- [ ] Replace abrupt carved shelves with supported bank geometry and varied silty margins. Keep channel widening explicit in artistic departures; dark damp margins must follow surviving canonical water polygons.
- [ ] Integrate broken material boundaries, selective dust, subtle sediment direction and sparse fragments. Match reference 01/04 lighting through soft key shadows and gentle neutral fill; compare offline and runtime shadow variants. Check AO/direct/self-shadow combination against a neutral-light render to avoid double darkening.
- [ ] Keep water opaque and pale with restrained moving glints; save a sharp still and 10-second clip. Add optional DOF only as a separately labelled photographic mode after sharp views meet V1–V5.
- [ ] Run shoreline tests, full suite, export validation and production build; inspect V2–V6 from the fixed poses. Commit `feat: integrate sculpted banks lighting and silty water`.

## Task 7: Evidence and human visual gate (VS5)

**Files:** Create `scripts/check-style-study.mjs`, `docs/style-patch-review.md`; modify README and PRD progress status only with verified results.

- [ ] Implement fixed-pose screenshot and orbit capture using the existing CDP transport approach, without importing regional performance pass criteria. Save resolution/DPR, engine/tool versions, config/map hashes and active geometry/material level in each capture manifest.
- [ ] Build a side-by-side reference board with images 01/03/04, final sharp captures, optional photographic view, neutral clay, normal/height/AO debug crops and the depth-technique comparison. Include fresh Blender-import captures from the same GLB.
- [ ] Run `npm test`, `npm run build`, package validation and all capture commands. Record exact commands and results, any shader/browser failures, and per-V1–V8 pass/fail reasons. Functional passing does not imply visual passing.
- [ ] Obtain independent review of code/portable exports; correct confirmed technical defects and preserve review evidence. Claude remains the requested independent reviewer where available, with no fabricated review if unavailable.
- [ ] Present the actual reference patch for user visual approval. Do not set VS5 complete or start VS6 on an agent/model's judgement alone.
- [ ] Commit evidence and progress status as `docs: record sculpted terrain patch visual review`.

## Deferred regional work

After VS5, plan regional rollout from the accepted recipe and observations. Derive
geometry, material and texture LODs at regional scale, verify spatial continuity and
then measure/adjust runtime policies. Engine adapters and delivery packaging consume
the portable asset contract; choosing another engine must not trigger re-authoring
of the sculpted surfaces or dependence on viewer-only palette reconstruction.
