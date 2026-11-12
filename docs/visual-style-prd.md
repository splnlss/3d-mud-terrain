# Visual style PRD: sculpted San Luis diorama

Status: visual direction approved; engine-agnostic clarification incorporated. Reference-patch implementation plan prepared for review; implementation has not begun.

## 1. Intent and priority

Create an explorable San Luis landscape that convincingly resembles a photographed,
hand-sculpted physical relief model. The viewer should perceive clumpy clay,
crumbled dark aggregates, worn ochre faces and pale silty channels at first glance.
The current smooth hills and patterned surface do not meet this requirement.

User direction: **visual quality first, performance second**. Establish a visibly
convincing patch before regional rollout or mobile optimisation. The terrain style
and detail are the product. Preserve the San Luis extent and subtle animated water.
PlayCanvas is the current preview adapter; 3D Tiles is a delivery option. Neither
may define the source asset format, material recipe or visual acceptance standard.

This document supersedes conflicting visual implementation prescriptions and
performance gate ordering in [the original PRD](prd.md), [design](design.md) and
[original tickets](tickets/README.md). It does not mark their open acceptance items
complete. The 60 fps / 150 MB / 5 MB / 200 draw-call figures become secondary
optimisation targets, not reasons to reject a necessary visual technique early.
No new mandatory performance numbers are invented here.

## 2. Reference authority

The [original Relief Pfyffer photograph](reference/relief-pfyffer.png) anchors the
physical material character. The five user-supplied generated studies define the
expanded desired appearance and composition. They are aesthetic targets, not
measurements, geographic evidence, or calibrated albedo/normal/height maps.
Where their lighting differs, use the explicit scene targets below.

| Reference | Primary use |
|---|---|
| [01 Braided channels](reference/style-studies/01-braided-channels.png) | Primary elevated view: dense irregular landforms, broad pale negative space, varied aggregates. |
| [02 Ridge level](reference/style-studies/02-ridge-level.png) | Material close-up: pinched ridge, irregular clasts, warm grazing light, photographic focus. |
| [03 Overhead delta](reference/style-studies/03-overhead-delta.png) | Overhead legibility: branching channels, islands, granular patches, broken material boundaries. |
| [04 Canyon](reference/style-studies/04-canyon.png) | Primary close-up: steep ochre faces, chunky dark deposits, embedded channel, scratches and worn edges. |
| [05 Layered peaks](reference/style-studies/05-layered-peaks.png) | Layered ridge silhouettes and depth, selective warm highlights, restrained background softness. |

Copies, checksums and original generation prompts live in
[style-studies](reference/style-studies/manifest.json). References remain unchanged;
new textures must be authored or baked separately, with provenance recorded.

### Engine-agnostic asset requirements

- Authoring output is a portable asset package, independent of the preview runtime.
  Preserve high-detail source geometry and editable recipes, linear height masters,
  PBR texture maps, simplified meshes and their error metadata. Never optimise away
  the source detail to satisfy one viewer's budget.
- Provide glTF 2.0/GLB with standard metallic-roughness materials, tangent-space
  normals, AO and ordinary image textures as a portable inspection baseline.
  Use metallic=0 for the earth materials. Height masters and material scale metadata
  travel alongside glTF because core glTF has no standard POM material definition.
- Meshopt, KTX2 and 3D Tiles are separately generated delivery variants. A consumer
  must be able to inspect the standard package without the PlayCanvas application,
  shader parameter names, tile URL parsing or viewer-only palette reconstruction.
- Record coordinate axes, units, georeference, normal convention, texture channels,
  material physical spans, height zero/range and LOD links in a versioned manifest.
  Core appearance survives import into another renderer; optional POM, self-shadowing
  and post-processing require consumer-specific adapters and need not be pixel-identical.
- Verify portability with Blender import/render plus the PlayCanvas preview from the
  same exported GLB/maps. Blender is an independent inspection consumer, not a second
  delivery-engine project. Standard exports must visibly retain the sculpted detail.

### Portable composition and texel density

Bake the clay/granular/dust blend into unique UV atlases for each inspection mesh.
Standard glTF materials bind the resulting base colour, normal, roughness and AO;
the exported look must not require a runtime ID-mask blend or triplanar shader.
Authoring may use triplanar projection, but bake that result into the portable maps.
Preview-only projection experiments are labelled and cannot close portability gates.
For a 2 km patch start with sixteen 500 m atlas cells, each 2048² (about 0.244 m per
texel on horizontal ground before UV packing/padding). Use 4096² for a cell where
close-up evidence needs it. Measure actual surface UV density on steep faces;
subdivide/repack rather than accepting stretched faces. Bake padded UV islands and
retain multiple ordinary-material primitives where needed; this is not a draw-call cap.

## 3. Experience and geographic identity

Visitors orbit, pan and zoom from an extent overview into material-rich local
views. Three saved review cameras expose elevated, overhead and close-oblique
views of the same patch. Optional photographic blur must never conceal defects.

Retain the roughly 112.64 km square centred on San Luis, major mountain/valley
relationships, Rio Grande route, Culebra range and Sanchez Reservoir identity.
Allow stronger local vertical shaping, clod displacement, bank shaping and
selective channel widening where they support the miniature read. Record these
as authored departures in a source-versus-stylised overlay.

Do not silently invent a regional braided river network to reproduce a generated
composition. Dense channels belong in a separate labelled material study where
needed; the geographic patch must demonstrate the style on real landform structure.
A proposed relocation of a major river, lake or mountain requires a separate design
decision. Roads/buildings remain absent; field patterns stay subordinate.

## 4. Visual requirements

| ID | Required appearance | Acceptance evidence |
|---|---|---|
| V1 Form | Irregular, pinched, chipped ridges with lobes, folds and occasional steep faces. Avoid uniformly inflated hills and uniform noise bumps. | Clay-only views from all three cameras show the structure without colour, normal maps or blur. Silhouette crops show actual irregular geometry. |
| V2 Aggregates | Dark crust consists of clustered, varied clasts separated by deep gaps, with isolated loose fragments and bare spaces. | Close view shows distinct clast tops, sidewalls and cavities; orbit reveals depth. It must not resemble fabric, scales, pebbled wallpaper or uniformly packed cells. |
| V3 Ochre and dust | Ochre clay has smoother worn faces, cracks/tool marks and dusty upper surfaces; dark deposits have broken boundaries. | Colour and neutral-light crops show both material families without continuous contour bands or generic camouflage blobs. Dust gathers selectively rather than washing out the scene. |
| V4 Contact | Clasts sit in the clay, deposits collect plausibly, and banks connect continuously to channels. | Close orbit shows no floating clasts, dark baked halos detached from objects, faceted shelves, holes or z-fighting. |
| V5 Water | Pale warm beige, opaque silty/painted water, broad enough to read within a bank; fine sediment streaks, subdued glints. | Still and 10-second clip show subtle shimmer without mirror reflections, foam, bright road-like strips or whole-surface flashing. |
| V6 Light | Warm directional key, soft cast shadows, dark but readable cavities, gentle fill, muted earth colours. | Neutral and final lighting captures preserve material identity. Highlights retain detail; cavities do not become black paint. |
| V7 Scale | A photographed miniature with coherent clod sizes and layered depth. | Same patch at three zooms; fine detail resolves into clusters nearby and merges naturally at distance without crawling or obvious repetition. |
| V8 Geography | Distinct San Luis structures survive the artistic treatment. | Source/stylised overlays and named landmark views demonstrate retention of the required major geography. |

Primary target composition is 01; primary surface target is 04. Images 02 and 05
justify an optional closer, lower oblique camera without requiring horizon or
unrestricted ground-level navigation. Camera limits may be revised after the patch
is convincing. Use image 03 to ensure the material also works without grazing light.

## 5. Normals, height and depth: required strategy

**Yes: normal and height maps are central to this revision.** The current normal
textures and custom lighting leave substantial quality unused. Use a coordinated
set of maps generated from a common sculpted surface, not independently invented
maps that describe incompatible features.

| Technique | Contribution | Limit and intended use |
|---|---|---|
| Baked normal map | Lighting detail for clod faces, cracks, pits, folds and tool marks. Combine mesoscopic normals with finer grain. | Does not move silhouettes, reveal sidewalls through camera translation, or independently cast geometric shadows. Required at all material detail levels. |
| Material height map | Scalar surface relief used by parallax or displacement; shared source for normals and cavity masks. | Not equivalent to camera depth. Single-valued height cannot describe overhangs or multiple surfaces at one location. Required authoring output. |
| Parallax occlusion mapping (POM) | View-dependent apparent depth and occlusion within granular clusters and clay creases. | More texture reads; cannot fix ridge silhouettes or physical water intersections. Required comparison prototype for close/mid views; promote only if it improves the moving view without distracting artifacts. |
| POM self-shadowing | Light blocked by small height features, strengthening the spaces between clasts. | Separate from baked AO and macro shadows; avoid multiplying the same darkness repeatedly. Evaluate on the reference patch. |
| Displacement / explicit mesh | True clod outline, ledge, ridge, bank and isolated fragment depth. | Requires sufficient vertices and correct normals/bounds. Bake offline into streamed meshes by default. Runtime displacement is optional, not assumed tessellation. |
| Scene depth texture | Camera-space depth for contact effects, optional SSAO and photographic depth of field. | Contains only visible geometry; cannot manufacture missing clasts or reconstruct hidden surfaces. Secondary polish, not a substitute for material height. |

### 5.1 Authoring and texture contract

- Build high-detail material exemplars for worn ochre clay, dark crumbly aggregate,
  dusty transitions and silty margins. Include clustered size variation, uneven
  packing, pits, scattered fragments, folds and sparse directional scratches.
- Bake unlit base colour, normal, height, roughness, AO/cavity and material ID masks
  from the same source. Keep lighting out of base colour. Preserve linear 16-bit
  or float height masters; document height zero and amplitude in scene units.
- Start material masters at 2K; use 4K when a close crop demonstrates insufficient
  detail. These are initial authoring settings, not fixed runtime dimensions.
  Select runtime resolution by visible texel density, then inspect compressed maps.
- Metadata records physical tile span, map conventions, channel packing, normal
  handedness, UV orientation, height range, authoring seed/version and source assets.
- AI-generated flat material studies may guide authoring. Do not treat brightness
  as height: shadows and highlights in photographs would become false geometry.
  Single-image estimated depth may seed a sculpt study, but is not an accepted
  multi-view terrain reconstruction or reliable displacement map.

Runtime height in the comparison must preserve the master's relief precision.
Decode linear 16-bit height on the CPU and upload a float texture where needed;
keep an uncompressed float baseline. Compare against any quantised/compressed
variant before accepting it. A 16-bit PNG file alone does not ensure a 16-bit GPU
texture after an engine image-loader path.

### 5.2 Normal mapping correctness

The present shader rotates the second sampling coordinates without reorienting
those sampled normal vectors, uses a tangent frame not derived from its projection,
and blends normals with a simple linear mix. These are code inspection findings;
visual impact must be isolated in the comparison patch before assigning blame.

Require a tangent frame consistent with the actual UV/projection Jacobian, correct
normal rotation for every rotated sample, normalisation after decoding/filtering,
and reoriented or equivalent detail-normal composition. Neutral normal maps must
reproduce mesh shading. Verify raised and recessed calibration shapes under a
rotating diagnostic light to catch flipped axes. Treat normal/height/AO/roughness
as linear data and base colour with the appropriate colour-space conversion.
Use a documented linear-light and output-tone pipeline rather than ad hoc gamma.

Use glTF tangent normals: RGB encode tangent X/Y/Z, with +X right, +Y up and
+Z outward. Texture (0,0) is the upper-left image corner. For the north-first planar
calibration fixture, image up corresponds to north; arbitrary UV islands use their
exported tangent basis, not a universal world-north assumption. Export MikkTSpace-
compatible tangents and verify a raised/recessed fixture under two light azimuths
in both consumers. The [glTF specification](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#materialnormaltextureinfo)
defines the interchange conventions.

Steep faces must retain detail density without streaking. Bake authoring projections
into proper UVs for portable acceptance. The former blanket prohibition on triplanar
mapping is withdrawn for authoring and labelled preview experiments. Reorient each
projection's normals correctly; multi-projection POM remains an experiment.
Use derivative-aware sampling, mipmaps and suitable filtering to prevent shimmer.

### 5.3 Parallax integration and boundaries

Pinned PlayCanvas 2.24.0 includes `PARALLAX_OCCLUSION`, `heightMapBase`, adaptive
sampling and optional `parallaxShadowSamples` in its StandardMaterial implementation.
Our terrain currently uses ShaderMaterial, so assigning those properties does not
activate that pipeline. Compare StandardMaterial plus targeted extensions with a
correct implementation in the custom shader; select the simpler path that meets V1–V8.

Apply the parallax hit coordinates consistently to the co-registered material maps.
Use the same height convention across authoring, normal derivation and ray marching.
For a square, uniformly scaled planar calibration material, normalised height
`h=(height-height_min)/height_range_m` has 1 at the top. The shader UV depth is
`height_range_m/span_m`, and geometry base is
`(geometry_height-height_min)/height_range_m`. Start base at 1 for cavity-only
relief. In PlayCanvas 2.24 the public `heightMapFactor` is multiplied by 0.1 before
upload, so set the public property to `10*height_range_m/span_m`, not the shader
factor directly. Confirm displacement against the geometric calibration object.
For packed/anisotropic UV islands, derive depth conversion from the UV-to-surface
metric; do not apply this planar scalar formula blindly to the whole atlas.
Shore fade and per-region amplitude are named shader-extension requirements.

Start the comparison at 16 and 32 maximum view samples with self-shadow off/on;
these are experiment settings, not claims about quality or speed. Test shallow,
steep and changing views, including texture seams and material transitions.

Fade parallax near tile/UV discontinuities and water boundaries using a shared,
world-consistent margin. Real geometry defines the water contact and silhouettes.
Do not let apparent relief slide across water, expose atlas neighbours, or change
bank clearance. Far views transition to normal-only detail without visible popping.
Retain a switchable normal-only baseline to identify the actual POM contribution.

### 5.4 Geometry, lighting and LOD

Separate three bands: DEM-driven major forms; sculpted mesoscopic ridge/clod/bank
geometry; mapped fine grain and pits. Each feature belongs to a declared band so
height, geometry and normals do not duplicate its full amplitude.

Initial scene-unit scale targets below are art-direction starting values, not
measurements recovered from generated images. Save changes with the recipe.

| Feature | Initial range in source metres | Close camera starting target |
|---|---|---|
| Visible clast diameter | 8–40 m, truncated log-normal, sigma 0.55 | Distinct multi-pixel clasts, roughly 5–40 px where in focus. |
| Aggregate cluster footprint | 60–300 m | Several clusters and bare faces visible simultaneously. |
| Ridge fold wavelength | 150–600 m | Silhouette changes visible without normal mapping. |
| Clast height / radius | 0.2–0.6 | Raised masses with sidewalls; no uniform spikes. |
| Close camera | 800–1600 m from target; start 1200 m, vertical FOV 40° | Tune framing to reference 04 and record the exact pose. |

Record `feature_scale_m` in recipe and manifest. Recipe must also name cluster
occupancy (start 35–65% within cluster footprints, under 10% outside), bare-clay
fraction, local cavity depth (start at least 0.15 of neighbouring clast radius),
sidewall angle (start 25–65°), slope/curvature/aspect placement weights and fall-line
scratch direction. Use slope/concavity to concentrate aggregates while leaving
exposed convex clay. Treat these as tunable shape constraints, not assertions that
all slopes must obey a physical erosion model. Roughness starts at 0.55–0.8 for
clay and 0.8–0.95 for aggregates, with sparse worn highlights allowed down to 0.35.
Review light and roughness together so the result remains dusty rather than lacquered.
Reject uniform-grid placement with a nearest-neighbour spread calibration; do not
require a multimodal histogram, since natural clustered samples can be unimodal.

Bake detail normals against each simplified LOD's actual surface, or demonstrate
that a shared residual normal is valid. Preserve important silhouettes and shore
vertices during simplification. Share boundary samples, texture padding and spatial
seeds across tiles; recompute bounds/geometric errors for displaced content.
Flattening every ridge is not an acceptable LOD optimisation.

Use a fixed warm key with soft shadows and neutral fill. Compare offline rendered
lighting against runtime soft shadows on the patch. Offline direct-light bakes are
reference-only unless packaged separately as an explicitly optional extension;
the standard PBR baseline must remain relightable. Store AO separately and avoid
baking direct light twice. Runtime shadowing, higher-resolution textures and extra
geometry are allowed where they visibly improve quality. Optional SSAO, depth of
field and grading come after the sharp, unblurred scene passes V1–V5.

### 5.5 LOD owns runtime detail allocation

Build the accepted highest-detail patch first. Derive lower-detail representations
from that master; do not design its appearance around a phone or engine budget.
Selection follows projected feature size/error and visible texel density.

| Band | Geometry | Materials and apparent depth |
|---|---|---|
| Close | Preserve clast silhouettes, ridge breaks and bank contacts. | Full normals, height/POM where supported, high-resolution maps and cavity detail. |
| Mid | Simplify small clasts into the parent surface while retaining important outlines. | Bake removed relief into residual normals/AO; lower texture resolution; reduce POM work as its visible contribution shrinks. |
| Far | Coarse terrain retains major ridge and water shapes. | Filtered colour/normal/roughness and broad shading; no unresolved parallax or fine geometry. |

LOD includes texture mip/residency, material complexity, shadows and geometry.
Mesh LOD alone cannot bound fragment shading or texture memory costs. Match these
bands by screen footprint so performance is governed by the detail actually visible.
Publish per-level geometric error, material spans, texture dimensions and transition
rules; adapters translate that metadata to their own selection systems. Validate
transitions in motion, including normal energy/roughness changes, clast disappearance,
shoreline stability and seams. Quality reductions cannot alter the saved masters.

## 6. Alternatives and decision

| Approach | Expected result | Decision |
|---|---|---|
| Improve normal maps only | Better lighting detail; smooth silhouettes and shallow-looking cavities remain. | Keep as baseline, insufficient final approach. |
| Rich maps + POM + selective geometry | Detailed clump interiors with convincing ridges, banks and orbit behaviour. | Recommended: first reference patch, then regional adaptation. |
| Dense sculpted geometry everywhere | Strong local depth but large authoring/data cost; distant detail is wasted. | Use as a quality reference and selectively retain visible geometry. |

## 7. Vertical slices and exit gates

Execution detail: [Reference patch implementation plan](superpowers/plans/2026-11-12-sculpted-reference-patch.md).

These replace the original performance-before-fidelity execution order. Every slice
ends with portable assets, a reproducible preview, saved camera poses and evidence.
Runtime-specific code is isolated in the preview/delivery adapters.
Do not rebake the full region until the reference patch passes VS5. Before VS5,
LOD work is a small fixture continuity proof; derive production patch/regional LODs
from the approved master afterwards.

| Slice | Deliverable | Exit gate |
|---|---|---|
| VS1 Reference patch and baseline | Choose a 1–2 km real patch with ridge, steep bank and mapped channel. Save existing render and source overlay. Add elevated, overhead and close cameras plus an adjacent labelled material exemplar if needed. | One command builds the patch package; a separate preview command exposes all three capture poses. The material study is clearly distinguished from San Luis geography. |
| VS2 Sculpted forms and aggregates | High-detail exemplars and actual mesoscopic ridge/bank/clod geometry, shown in neutral clay in Blender, then the preview adapter when available. | V1/V4 pass without textures or blur; no smooth dune field, floating deposits or generic repeated bumps. |
| VS3 Normal and height comparison | Coherent material maps; switchable baseline, corrected normals, POM, POM with self-shadow and geometry reference on the same patch. | Neutral-map and lighting-direction checks pass. Side-by-side orbit clips show what each method adds; chosen method has no inverted, swimming or stretched relief. |
| VS4 Integrated material, light and water | Broken ochre/dark transitions, selective dust, soft lighting, natural bank contact and subtle silty shimmer. | V2–V6 pass at all three cameras, including sharp images with effects off and a moving clip. |
| VS5 Visual acceptance | Evidence board against references 01/03/04, plus optional photographic view referencing 02/05. Record each V1–V8 result and reviewer notes. | User approves the patch's visual look. V1/V2/V4 must also pass on the fresh Blender import of standard GLB/maps at the close camera, without POM or custom shaders. A technical or model review alone does not close this gate. |
| VS6 Regional rollout | Apply the accepted recipe to Culebra, Rio Grande gorge, Sanchez Reservoir and valley fields, then full extent. | V1–V8 reviewed at named views, geography retained, tile seams and LOD transitions inspected in motion. |
| VS7 Performance refinement | Measure accepted high-quality scene; introduce documented quality presets and streaming refinements. | Publish actual device/viewport/frame-time/memory/transfer results. Any downgrade must retain approved visual traits; unresolved target misses remain explicit. |

## 8. Evidence and acceptance procedure

For each slice save bake/config/asset hashes, viewport and DPR, camera, sun/fill,
exposure/tone settings, engine version, screenshots and orbit clip. Review at 1920×1080
and a fixed portrait viewport. Record exact capture settings; emulation is not a
physical phone benchmark. Match reference apparent feature scale before comparing.

For each V criterion record pass/fail, crop links and a concrete reason. Use neutral
clay, normal visualisation, height, AO-only, roughness and final-colour debug views
to distinguish faults. Show blur-off captures alongside any photographic treatment.
Do not use average colour, image similarity scores, test counts or frame rate as a
proxy for style approval. AI review is advisory. User judgement closes VS5 and final
visual acceptance; a failing criterion remains open with a named follow-up.

Technical checks cover map conventions, deterministic bakes, edge continuity,
normal/height alignment, shader compilation, resource disposal, compressed texture
fidelity, glTF/bounds validation and water contact across LODs. Tests supplement
visual evidence; they do not establish resemblance.

## 9. Performance policy, risks and non-goals

Record frame times, residency, compressed transfer, draw calls and visible loading
behaviour from VS1 onward so costs are understood. Optimisation work follows visual
acceptance, unless a crash, exhausted memory or stalled interaction prevents review.
The highest-detail portable assets establish the look. Runtime presets and
LOD policies may adjust POM samples, texture resolution, shadows and geometry
according to screen footprint. They must be reviewed independently.
The original phone targets remain aspirations until actual hardware measurements;
missing them does not authorise silently removing defining visual features.

Main risks: over-amplified POM at grazing angles; seams and shoreline mismatch;
over-darkened AO/self-shadows; stretched steep faces; excessive noise/repetition;
loss of geographic identity; and texture/data growth. Use the comparison controls
and patch gate to resolve these before regional rollout.

Non-goals: runtime erosion, water simulation, extracting reference-image textures,
Google-derived geometry, reconstruction of the entire model from a photograph,
unrestricted ground exploration, or building another full runtime application. Overhangs are optional local mesh
features; POM and terrain heightfields cannot represent them faithfully.

## Review record

[Claude style-plan review](claude-style-review.md) preserves the original findings,
host verification and documentation corrections. The review predates the corrections;
no subsequent Claude approval is claimed.

## 10. Technical sources

Checked against the installed PlayCanvas 2.24.0 source and official documentation:

- [PlayCanvas parallax mapping](https://developer.playcanvas.com/user-manual/graphics/physical-rendering/parallax-mapping/): offset/POM modes, height conventions and sampling tradeoffs.
- [StandardMaterial API](https://api.playcanvas.com/engine/classes/StandardMaterial.html): normal/height maps, parallax and material integration.
- [PlayCanvas lightmapping](https://developer.playcanvas.com/user-manual/graphics/lighting/lightmapping/): external baked soft shadows and indirect lighting.
- Local engine: `node_modules/playcanvas/build/playcanvas/src/scene/shader-lib/glsl/chunks/standard/frag/parallax.js` and `scene/materials/standard-material.js`.
- Current implementation inspected: `bake/shape.py`, `bake/material.py`, `src/materials.ts`, `src/shaders/terrain.frag`, `bake/pyramid.py` and `bake/tile.py`.
