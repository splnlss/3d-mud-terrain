# Claude handoff: reference-driven terrain appearance

Snapshot: 2026-11-12. **Visual result rejected; work in progress.**

## Update 2026-11-13

The direction below was superseded by a user-approved look. Start with the
[relief process](relief-process.md) and the [real-patch boards](reviews/relief-patch/README.md);
the rest of this file is history.

## Start here

1. Inspect git status and repo instructions in the current workspace.
2. Open the actual reference images linked in [PRD reference authority](visual-style-prd.md#2-reference-authority): original, then 01–05. They alone define the look. Verbal material labels and earlier model critiques are not substitute targets.
3. Read the [PRD](visual-style-prd.md), then the summary table at the top of the [failed-attempt ledger](style-patch-review.md). Open the linked rejected renders beside the references.
4. Inspect the relevant source below before choosing the next implementation. Continue toward a small image-matched patch; evaluate shape, connected detail, colour and highlights together. Current algorithms are experiments, not an approved recipe.

## User intent and latest corrections

- Real San Luis geography, approximately 70 × 70 miles centred on San Luis. The current 2 km Culebra foothill patch is the visual development area.
- Terrain style/detail first. Preserve high-detail sources; derive geometry, texture and material LOD after the appearance works.
- Engine-agnostic authored assets. PlayCanvas is a preview adapter; 3D Tiles is optional delivery. The delivery engine is not the current blocker.
- Normal and depth maps should contribute real surface detail, alongside necessary geometry. Material response and reflectivity must resemble the supplied images.
- The user explicitly rejected the later textured pass: “yeah not close”. They asked if low-poly limits were responsible. **They were not:** source meshes were dense; the form, distribution and material choices were wrong.
- Latest instruction: “Please only use the images as a source not what I say.” Apply this to visual authority. A preceding “large sandbox” description must not introduce a box, sand-pile rules, tool marks or other imagined requirements. Other functional/geographic requirements still apply.

## Current git and transfer state

- Worktree: `/Users/splnlss/.paradev/worktrees/3d-mud-terrain/creating-3d-terrain-from-e4ea3c35`.
- Branch: `colorado-mud-terrain-e4ea3c35`.
- HEAD at snapshot: `642e578` — WIP ridges/crust/banks.
- Upstream: `origin/colorado-mud-terrain-e4ea3c35`, at `1102184`.
- Eight local commits after upstream contain the PRD, reviews and initial patch pipeline. Later texture/study work and this handoff are **uncommitted**. Nothing from this session has been newly pushed.
- Continue in this worktree to retain those files. A remote checkout alone omits the eight local commits, untracked source/evidence and ignored `data/` packages. Refresh git state before any integration action.

### Uncommitted work to preserve

Inspect `git status --short` for the exact inventory. Important files include:

- Modified [source preview](../bake/style/blender_preview.py), PRD, material-study provenance and visual-review notes.
- New [shared fragment builder](../bake/style/clast_mesh.py), [stamp baker](../bake/style/material_stamp.py), [stamp conversion](../bake/style/stamp_maps.py), [first texture preview](../bake/style/textured_draft.py).
- New [granular-map authoring](../bake/style/granular.py) and [material refinement renderer](../bake/style/material_refinement.py).
- New [continuous study authoring](../bake/style/clay_study.py), [study renderer](../bake/style/blender_clay_study.py), [pinned scan downloader](../bake/style/fetch_clay_scan.py).
- New [granular tests](../tests/test_granular_material.py), [study tests](../tests/test_clay_study.py), generated colour candidate and review images under `docs/reviews/`.

## What exists technically

The committed pipeline in `bake/style/` includes:

- `patch.py`, `package.py`, `__main__.py`: pinned DEM window, coordinate/source metadata, NHD clipping, staged package publication.
- `surface.py`, `author.py`, `maps.py`: world-coordinate sculpt/deposit fields, material masters and coherent height/normal data.
- `shore.py`, `refine.py`: DEM-supported mapped channel, bank integration, source regeneration and stale-export marking.
- `atlas.py`, `export.py`, `blender_bake.py`: sixteen-cell standard GLB baseline and image atlases. The current atlas method is not a faithful bake of all latest high-detail source geometry/materials.
- `lod.py`: small geometry and residual-normal continuity fixtures. Production regional LOD is pending visual acceptance.

Source config: [patch](../configs/style-patch.json), [material recipe](../configs/style-materials.json).
Editable package, if still present locally: `data/style-patch/`.
Source is an 801 × 801 authored surface, with approximately 76,000 instanced fragments at the last regional-source pass. The 1.2 m specimens use a separate dense surface and do not represent San Luis geometry.

## Evidence to inspect

| Evidence | Meaning |
|---|---|
| [Original viewer close](evidence/08-close.jpg) | Early rejected regional implementation. |
| [First textured channel](reviews/texture-draft/channel.png) / [detail](reviews/texture-draft/detail.png) | Plate-like texture, stretching and scattered dark fragments; rejected direction. |
| [Latest regional material](reviews/texture-draft/refined-channel.png) / [detail](reviews/texture-draft/refined-detail.png) | Material v6. Actual Blender source render; still rejected by user. |
| [Before/after](reviews/texture-draft/material-comparison.jpg) | Same detail camera, but exposure/material/light fill also changed; not an isolated texture comparison. |
| [Continuous specimen](reviews/clay-study/procedural-study.png) | Too smooth, regular ridges/grooves, dark round spots. |
| [Relief specimen boards](reviews/relief-study/README.md) | Later image-matched specimen with reference/render boards; awaiting user judgement, gaps listed there. |
| [Scan specimen](reviews/clay-study/scan-study.png) | Registered scan detail; too uniformly grey and lacking the reference's larger connected structures. |

The last two specimens were self-assessed as failed diagnostics; they were not separately approved or explicitly rejected by the user. The latest user instruction changed visual-source authority, not approval status. No new image-matched render was made after that clarification.

## Review status and limits

- [Claude plan reviews](claude-style-review.md): earlier blockers closed; “Ready to start” meant plan readiness, not a visually approved result.
- [Material critique](reviews/texture-draft/claude-material-review.md) and [follow-up](reviews/texture-draft/claude-material-followup.md): advisory comments on v2/v4, not acceptance of final v6 or the specimens.
- Earlier critique transcribed in the ledger contains categorical interpretations such as all peaks needing a particular profile. Check those against the images; do not adopt them as requirements.
- User acceptance VS5 is open. No final moving-camera comparison or current-style portable import verification exists.
- New experiments are offline Blender source views. The browser and old exported GLBs do not show them.

## Local generated state and reproduction cautions

`data/` is ignored. Important local outputs:

- `data/style-patch/source/`: raw DEM, sculpted fields, clast records, water mesh, original master and separate `material-v6.blend`.
- `data/style-patch/review/`: intermediate v2–v6 renders/settings, source views and old portable views. Names containing “portable” are older, stale evidence.
- `data/granular-stamp/`: geometry-baked height/normal/AO plus packed raw maps.
- `data/clay-material-v2/`: independent authored granular maps; `material-draft.zip` contains images and finish notes, not a validated final material.
- `data/clay-study/`: dense specimen fields and packed study scenes.
- `data/materials/brown-mud-03/`: downloaded CC0 maps and checksum/provenance JSON.

**Inspect before rerunning authoring.** `npm run bake:patch` rebuilds the raw package;
`bake.style.author` can replace refined fields. `npm run refine:patch` reauthors the
source from the preserved DEM and marks delivery exports stale. Existing scripts
are reproducible experiments, not a reason to repeat the rejected output.

The [ledger](style-patch-review.md) preserves commands for each experiment. Source
data is cached locally; large DEM/source downloads are not committed.

## Verification checkpoint

Last full test run before this documentation-only handoff: **58 Python + 8 TypeScript tests passed**, recorded in local `data/clay-study-tests.log`.
The study renders completed with Blender exit 0; Python compile and whitespace checks passed. This verifies technical execution, not resemblance.
The earlier production build passed with the existing Vite chunk-size warning; it was not rerun for this documentation handoff.
The old sixteen GLBs previously validated; the current package is intentionally stale and must not be described as currently validated.

For new implementation work use the repo's current test/build scripts and preserve the visual evidence. A successful test run cannot close a visual gate.

## Next useful result

Produce one genuinely image-matched patch and a clear reference/render comparison,
with the actual geometry/material source, recorded settings and a sharp capture.
Evaluate silhouette, nested connected detail, material boundaries and selective
highlights as a whole. Normal maps alone cannot fix the current shape/distribution
errors. Transfer any accepted specimen work onto the real patch, then rebake the
portable package and verify the same appearance through a fresh import. Regional
rollout and production LOD remain downstream of visual acceptance.

### Prompt to resume

> Continue from `docs/claude-handoff.md`. Inspect git status and the supplied images first. The latest renders were rejected; the images are the sole visual authority. Review the failed attempts before choosing a new approach, then continue toward one image-matched patch. Preserve the current uncommitted work and distinguish technical checks from visual acceptance.
