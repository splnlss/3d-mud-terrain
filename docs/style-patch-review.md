# Failed visual attempts and current state

Snapshot: 2026-11-12. **No accepted visual result.**
Read the supplied images and [current visual PRD](visual-style-prd.md) first.
For resume instructions and exact workspace/asset state use [Claude handoff](claude-handoff.md).

## Failure ledger

| Attempt | Evidence / implementation | Outcome and lesson |
|---|---|---|
| Original regional viewer | [Close render](evidence/08-close.jpg), other named views in `docs/evidence/` | User described the quality as subpar and unlike the source. A functioning geographic viewer did not establish the required surface appearance. |
| Early dense source: rounded masses and compound clasts | `surface.py`, `blender_preview.py`; original critique transcribed below | Rounded masses read as inflated domes; compound sphere groups read as separate raspberry-like clusters. Dense geometry itself was not the missing ingredient. Early review advice was an art hypothesis, not a new style specification. |
| Ridge segments, shelves, denser fractured clasts and mapped banks | [Source close view](reviews/shape-draft/source-close.png); current `configs/style-materials.json` | Sharp peaks, repeating ridge profiles and scattered plate-like chips persisted. More fragments and steeper crests changed the object without establishing resemblance. This source is approximately 801² vertices plus 76k instances, not a deliberately low-poly render. |
| Generated granular stamp image | [Image study](reference/material-studies/granular-study-v1.png) | Contained baked lighting. Kept only as a shape study; explicitly not interpreted as height/normal data. A plausible image is not a coherent relightable material. |
| Geometry-baked granular stamp on terrain | [Channel](reviews/texture-draft/channel.png), [detail](reviews/texture-draft/detail.png); `material_stamp.py`, `stamp_maps.py`, `textured_draft.py` | Added grain, but plate/crackle character, steep-face stretching and detached fragments remained. Height was baked but this preview used normal/AO/roughness shading, not terrain displacement. |
| Reference-guided colour plus independently authored granular relief, v2–v4 | [Colour candidate](reference/material-studies/clay-albedo-v2.png); `granular.py`, `material_refinement.py`; [Claude critique](reviews/texture-draft/claude-material-review.md) | v2 became too dark and uniformly gritty, with misplaced wet sheen. Fill, colour and roughness adjustments improved some cues. Generated colour retained residual shading and was not point-for-point registered to authored relief. This is not an accepted production PBR set. |
| Colour/finish iterations v5–v6 | [Latest channel](reviews/texture-draft/refined-channel.png), [detail](reviews/texture-draft/refined-detail.png), [comparison](reviews/texture-draft/material-comparison.jpg); [Claude follow-up on v4](reviews/texture-draft/claude-material-followup.md) | v5 pushed crust too blue and exposed water triangle highlights. v6 corrected tint and water shading, but the user still said “yeah not close”. Conical forms, plate fragments and weak connected detail remained. Adjusting hue/specularity over the wrong forms was insufficient. |
| Continuous procedural specimen | [Render](reviews/clay-study/procedural-study.png); `clay_study.py`, `blender_clay_study.py` | Self-assessed failure: regular ridges/grooves, smooth dark dots and overly soft surfaces. Continuous geometry alone did not reproduce nested irregular detail. This is a 1.2 m diagnostic specimen, not the San Luis patch. No user approval. |
| Registered scan on specimen | [Render](reviews/clay-study/scan-study.png), [notes/provenance](reviews/clay-study/README.md); `fetch_clay_scan.py`, study renderer `--scan` | Self-assessed failure: finer registered material detail, but too uniform/grey and lacking the large connected features and colour boundaries visible in the references. Generic mud texture was not a substitute for image matching. No user approval. |
| Image-matched relief specimen | [Boards and notes](reviews/relief-study/README.md); `relief_study.py`, `blender_relief_study.py` | User called the direction good and listed mound shape, clay detail and nodules as still off; refined since. Self-assessed as the first result in the reference family (connected nodule crust, ochre faces, pale channel), with listed gaps in mound roundness, apron extent and fine clay detail. Specimen only; not transferred to San Luis. |
| Relief style on the real patch | [Boards and notes](reviews/relief-patch/README.md); `relief_patch.py` | Open, awaiting user judgement. Creek from NHD, gully from DEM drainage, land from DEM height above channel; fields, crust and light/dark tone from NAIP imagery. Source render only, no portable export yet. |
| Verbal “sandbox” interpretation | No new sandbox-specific geometry or material was made; only exploratory asset lookup | Superseded by the user's explicit instruction to use only images as visual authority. Do not use a verbal analogy or material name to invent the appearance. |

The specimens were self-assessed as failed diagnostics. The explicit latest user
rejection concerned the regional material result; do not invent user feedback on
images they did not separately evaluate.

## What failed in the process

- Procedural shape formulas were chosen before demonstrating their visual fit,
  then colour, noise and roughness were adjusted around those wrong forms.
- Each local correction was treated too optimistically. Claude's observations
  sometimes became implementation prescriptions instead of being checked against
  the actual reference images. Earlier reviews disagree about crest/cluster forms;
  resolve that through the images, not by choosing one review as authority.
- Small-scale grain was added while larger connected deposits, material transitions
  and silhouette variation were still wrong. A high polygon count did not fix that.
- Some material changes also changed exposure/fill, so their comparisons cannot
  isolate the texture's contribution. Preserve settings and matched views next time.
- Generated colour and independently authored relief were not fully registered;
  residual painted shading could conflict with actual highlights.
- The specimens exposed additional problems but were not transferred back onto
  the real terrain. They cannot close geographic or portable-package acceptance.

## Reusable technical work and open gates

Reuse deterministic inputs, coordinate conventions, staged publication, actual
mapped water, explicit stale-export rejection, normal/height fixtures and the
standard GLB baseline where useful. Re-evaluate artistic recipes from the images.

Last full test run: **58 Python + 8 TypeScript passed** (`data/clay-study-tests.log`).
These counts demonstrate technical checks, not visual similarity. No new test run
is claimed for this documentation update. The latest Blender study renders exited
successfully; the older sixteen-cell GLB validation predates all recent source
changes. Browser technique comparison, current portable parity, moving-view
acceptance, production LOD and VS5 user approval remain open.

## Reading the historical notes below

The following chronological record preserves experiments, exact critiques and
commands. Its “current/latest” labels and older test counts refer to the time of
each entry. They do not override the summary above or the image-only PRD.
Quoted critique is advisory, and comments about a material's physical identity or
how it was made are reviewer interpretations rather than established facts.

# Historical implementation notes

The selected source is a 2 km Culebra Creek foothill reach near -105.27, 37.18.
[Patch configuration](../configs/style-patch.json) pins the input hashes and records
why the flatter Rio Grande gorge candidate was rejected. [Authoring recipe](../configs/style-materials.json)
records the current spatial scales. No visual acceptance is claimed.

## Current status

- Raw package boundary/publication tests pass; a real DEM/NHD patch was generated.
- Authored source includes ridge shaping, editable compound clast geometry, coherent
  height/normal/PBR masters, mapped water and a staged visual-refinement command.
- Initial portable export: sixteen GLBs, 32 material primitives, no validation errors;
  fresh Blender imports rendered. These exports predate the current visual changes
  and are **stale** until rebuilt and independently reviewed.
- Small geometry/residual-normal LOD fixtures exist. No production LOD derivation
  or full-region rollout has been performed for this visual revision.
- Browser depth-technique comparison, final integrated water animation, matched
  camera evidence and user acceptance remain open.

## Visual iterations

The first source scene was still smooth terrain with scattered flat rocks. Tests
reproduced and corrected their failure to conform to a sloped surface. Later
compound meshes created actual cavities, but appeared like separate raspberry
clusters. A focused independent Claude visual critique judged the result **not
close**, with morphology, distribution and material response still substantially
wrong. Raw critique and images supplied are preserved in ignored
`data/claude-patch-art/`; the exact response is below.

Current changes respond to that critique: shorter ridge segments replace broad
elliptical domes; aggregate diameters are now 4–16 m rather than the initial 8–40 m
art guess; more small clasts are embedded into the surface; slope-aligned wear,
shelving and actual high-detail geometry replace uniform bumps. Curvature-sign
regressions ensure exposed convex tops and cavity collection are not reversed.
The source preview now consumes crust and dust masks. These changes are candidates,
not proof of reference fidelity.

Authored surfaces are computed at 2.5 m spacing from the preserved 10 m DEM. Local
wear/material filtering requires an 80 m processing halo; delivery cells crop one
global patch. The world-coordinate crop test compares valid interiors with that
halo. Regional chunking must retain equivalent context.

## Evidence locations and limitations

- `data/style-patch/review/source-close.png`: latest Blender source authoring view.
- `data/style-patch/review/iteration-03-close.png` and `iteration-04-close.png`: saved
  intermediate morphology views, with different settings where recorded in history.
- `data/style-patch/review/portable-close.png`: older fresh-import baseline, not the
  current source result.
- `data/style-patch/manifest.json`: recipe, camera, source hashes and render settings.

A new browser/Blender comparison board will be published after the visual result is
credible. Current technical checks do not close V1–V8 or VS5. Source procedural
material nodes must be baked into portable maps; a good source view alone cannot
close the engine-agnostic acceptance gate.

## Independent visual critique (verbatim)

Honest match first: this is not close. Composition is in the right family (mounds, a channel, dark material), but silhouette, material, clast morphology and lighting are each wrong, and together they read as a toy render rather than a wet clay model. I would put it at roughly a quarter of the way to the Relief Pfyffer look.

What the render shows versus the references:

- **Silhouette.** The current landforms are overlapping hemispheres with soft crests. The references are conical peaks and ridge lines with concave flanks, crumbled crests and shelved terraces. No mound in any reference has a round top.
- **Clasts.** The render has discrete raspberry blobs resting on the surface, each a sphere studded with spherical lobes. The references have contiguous crusts of small, irregular, angular nodules fused into the flank, with the clay smeared over and between them, dense where they occur and sparse elsewhere.
- **Clay surface.** The render has isotropic felt-like grain. The references have fall-line striations, finger drag marks, cracks, embedded grit and stepped shelves.
- **Colour.** The render spans narrow beige to light brown. The references run from near-black wet grey through ochre to pale cream dust, with golden crest highlights and dark gully shadow.
- **Lighting.** The render is a mid-elevation key with flat fill. The references are low raking warm light with hard shadows, specular sheen on wet clay and shallow depth of field.

Ordered actions, highest impact first:

1. **Replace the dome profile with ridged cones (code-backed).** In clay_stamps the mass is a paraboloid raised to the 0.85 power, which rounds the crest further, with an aspect ratio near one half and a hard max union. That is exactly the bubble field in the image. Use a profile that is concave up the flank, for example one minus the square root of the radial term, raised to a power above one, and build each mass as a short ridge segment rather than an ellipse so crests become lines. Replace the max union with a smooth max and add a crest-sharpening term so overlaps form saddles and spurs, not fused bubbles. The 24 m fold term is swamped by 35 to 85 m stamps and is gated by source slope, so the stamps themselves carry no folds. Regate on the shaped slope after stamps.

2. **Add fall-line striation and shelving (code-backed).** The config field for striation direction is never read. The grain term is isotropic value noise at 4 to 9 m on a 2.5 m grid, which produces the uniform felt. Replace it with anisotropic noise sampled in a gradient-aligned frame, high frequency across slope and low along it, gated by slope. Add a terrace term that quantises height on steep flanks with a noisy offset, giving the stepped shelves visible on every reference peak.

3. **Embed clasts and make them a crust, not scattered rocks (code-backed).** Clasts are lifted by 8 percent of their height radius, so they sit on the skin. Sink them by 30 to 40 percent of height. Each template adds thirty near-spherical lobes to a sphere, which is the raspberry. Use fewer, larger, flattened lobes with noise displacement and angular facets. Shrink the radius range toward 2 to 8 m and multiply the per-cluster count several times so nodules abut and merge. Add a heightfield crust displacement where cluster density is high, so the terrain itself becomes granular under and between clasts. The occupancy target in the config is not being met visually, and the counts formula explains why.

4. **Move clusters off crests onto flanks and gullies (code-backed with an art hypothesis).** Cluster ellipses are laid out on a grid independent of the terrain, so they straddle mound tops. The convex exposure penalty is weak because large rounded stamps have low curvature magnitude. Derive cluster centres from the shaped terrain, favouring steep concave flanks and channel bases, and bias deposits toward the shaded aspect. Hypothesis: the references show aggregate concentrated on the lower two thirds of flanks with ochre crests nearly always clean.

5. **Drive material from the authored masks (code-backed).** The preview loads only heights and clasts. The crust, dust and cavity masks are computed and never used. Feed them in: pale dust on low-slope areas, dark wet grey in cavities with a roughness near 0.35 and a visible specular lobe, ochre to gold on exposed crests. Widen the clay ramp well beyond its current range and give the dark material its own hue variation and speckle. Add a cavity-depth bump that is at least the configured 0.15 of radius, which the current bump distance does not reach.

6. **Relight and reframe like the photographs (art hypothesis, partly code-backed).** The sun sits about 32 degrees up with a tiny angular size and a flat world fill. Drop it to 15 to 20 degrees, place it side-back relative to the camera, raise its energy and angular size slightly, and cut the world level so gullies go dark. Add depth of field with the focus plane on the mid-ground. Lower the camera pitch toward 25 degrees. The water should become grey-beige silt with low roughness, swirl marks and a raised shoreline lip. The current sawtooth cut where the terrain meets the water plane is a visible mesh artefact that any photo-style lighting will emphasise.

Items one through three change the most pixels. Without one and three, items five and six will only make a better-lit version of the same wrong object.

## Further source refinements

The later passes use flatter fractured clods and a separate fine-crust band of
actual surface-oriented nodules. That band is denser on steep dark faces and absent
from flat dust in a numerical fixture. Coarse vertical height displacement was
removed after it visibly stretched/melted steep faces. Fragment embedding is tuned
against the actual template bounds, rather than treating every source shape as a
unit sphere. The latest close camera is also being tested along the creek.

The source package records `exports_status` after each refinement. The validator
now rejects stale delivery assets, so the older 16-GLB format result cannot be
mistaken for a validation of the current authored scene. Latest numerical suite:
56 Python and 8 TypeScript tests passed; production build passed with the existing
Vite bundle-size warning. These results do not imply visual acceptance.

## Textured draft — 2026-11-12

The next visual probe combines the existing sculpted source mesh with a
geometry-derived granular texture. It does not require the mesh silhouette to
be final before judging the surface.

Reproduce:

```sh
blender --background --python-exit-code 1 --python bake/style/material_stamp.py -- --output data/granular-stamp --resolution 2048
uv run python -m bake.style.stamp_maps data/granular-stamp
blender --background --python-exit-code 1 --python bake/style/textured_draft.py -- --package data/style-patch --stamp data/granular-stamp
```

The 64 m repeat contains deterministic authored fractured geometry, baked into
linear normal, height and ray-traced AO maps. Height spans 0–3.242 m in the
current stamp. PNG normal, 16-bit height, float height and ORM outputs are
engine-independent. Height and roughness are available for later displacement
and material LOD; this draft uses tangent-space normal shading, cavity shading
and height-dependent roughness. It does **not** displace the terrain with the
stamp. AO remains separate from intrinsic colour; the source preview multiplies
it in the material because Blender Principled has no separate AO input.

Outputs are `data/style-patch/review/textured-close.png`,
`textured-detail.png` and the packed editable `source/textured-draft.blend`.
The original master and old GLB exports are not replaced. This is an offline
source preview, not proof of the PlayCanvas or GLB result. Visual acceptance
remains open.

Observed after rendering: the texture adds visible surface grain, but the
planar mapping stretches on steep faces and the large dark fragments still
read as scattered additions rather than fused crust. The material appears too
uniform and pale compared with the canyon reference. These are unresolved
visual gaps. Next refine surface projection, material colour variation and
fragment integration together. Portable review copies are in
`docs/reviews/texture-draft/channel.png` and `detail.png`.

## Material refinement v2

User requested closer colour, texture and reflectivity. New colour candidate:
`docs/reference/material-studies/clay-albedo-v2.png`, guided by canyon study 04.
Independent fused granular relief replaces the previous plate-like height
stamp. `bake/style/granular.py` writes 2K normal, 16-bit height, AO, roughness,
wetness, dust and ORM maps with a 32 m repeat. Current height range is
0.00456–0.46511 m; roughness is 0.383–0.96. Low-frequency finish patches create
variation between satin clay and matte dust. This is an artistic interpretation,
not a measured BRDF fit to the photograph.

`bake/style/material_refinement.py` applies the colour and physical height using
world-space box projection with blending on steep faces, plus fine pore bump.
The same colour family on the fragments reduces the disconnected dark-chip
appearance. Dielectric IOR is 1.48, specular IOR level 0.45, no clearcoat.
The source geometry and lighting remain unchanged, but exposure is reduced
from +1.0 to +0.1 stops; comparisons therefore include this exposure change.
The current shader uses height bump, not displacement; normal maps remain
available for portable export. Generated colour retains residual shading and
is not exactly registered to the authored geometry maps.

```sh
uv run python -m bake.style.granular --output data/clay-material-v2 --resolution 2048
blender --background --python-exit-code 1 --python bake/style/material_refinement.py -- --package data/style-patch --maps data/clay-material-v2 --albedo docs/reference/material-studies/clay-albedo-v2.png
```

### Independent material review and follow-up

Claude's read-only art review is saved in
`docs/reviews/texture-draft/claude-material-review.md`. It found v2 too dark,
uniformly gritty and short of satin sheen. Accepted follow-ups: lift ambient
fill, use spatially varied grey/ochre tint, reduce pore bump, suppress granular
relief on exposed clay, and lower the dry clay roughness range. The next pass
uses dry roughness approximately 0.53–0.76, with a 0.43 shoreline finish.
The pale channel is muted from nearly white to taupe and given glancing sheen.

Claude interpreted the canyon reference channel as wet mud. This is plausible
for that study but does not replace the agreed opaque silty-water requirement;
the mapped channel remains water. Its appearance is refined instead. The
remaining conical silhouettes, flat plate-like clasts and abrupt banks are
source geometry problems, not solved by these material changes.

Claude's follow-up on v4 confirmed a material improvement and identified two
remaining gaps: insufficient cool/dark crust versus pale matrix separation,
and the conical landform language. The follow-up is saved alongside the first
review as `claude-material-followup.md`. The final material pass in this iteration
reduces matrix colour saturation to 0.65, crust saturation to 0.25, adds a cooler
crust tint, and lightens silt. Water shading uses smooth normals to remove
triangle highlights exposed by the new sheen. This changes shading normals,
not mapped water positions. Render names are `material-v5-close.png` and
`material-v5-detail.png`. These remain source previews; old GLB exports are stale.

### Current reviewed source draft: material v6

Current source shader is `bake/style/material_refinement.py` (default tag v6).
After checking v5, the crust was pulled from blue-grey back toward warm charcoal.
Silty water now uses a constant upward shading normal and roughness 0.48; this
removes the triangular specular pattern without changing its mapped positions.
Current review copies: `docs/reviews/texture-draft/refined-channel.png` and
`refined-detail.png`. These replace no earlier evidence. Quality remains below
the photo target: silhouettes are too conical and nodules too plate-like; coarse
stratified relief, clod clustering and clay/crust transitions need further work.
Generated colour is a draft with residual shading, and authored microrelief is
not point-for-point registered to it. No visual acceptance or GLB parity claimed.

## Rejected direction and continuous clay study

User rejected material v6 as still not close, then asked whether low-poly
constraints caused the mismatch. They did not: the source was dense and no
performance budget constrained these previews. The failed choices were pointed
landform stamps, flat plate fragments, excessively uniform microtexture, and
trying to fix their read mainly through colour/roughness.

A bounded physical specimen is now authored by `bake/style/clay_study.py` and
rendered by `bake/style/blender_clay_study.py`. It uses one continuous height
surface: rounded ridge crests, concave slumped flanks, incised downhill runnels,
embedded rounded grain clusters, smooth clay and physically varied finish.
Colour, roughness and depth derive from the same fields, with no generated
colour image or baked lighting in albedo. Lighting is a warm grazing key and
soft sky fill, with physical camera depth of field at actual specimen scale.

This 1.2 m specimen is explicitly a shape/material calibration study. It is not
San Luis geometry, and is not presented as a completed regional terrain render.
Once the surface language works, its authoring rules can be transferred to the
geospatial source. The previous region renders remain rejected evidence.

```sh
uv run python -m bake.style.clay_study --output data/clay-study --resolution 1400
blender --background --python-exit-code 1 --python bake/style/blender_clay_study.py -- --study data/clay-study
```

The first continuous specimen also failed visually: too smooth, with dark round
spots rather than crumbly crust. It is diagnostic evidence, not an accepted
look. A second comparison uses the registered `brown_mud_03` source maps by
Rob Tuytel, [Poly Haven](https://polyhaven.com/a/brown_mud_03),
[CC0](https://polyhaven.com/license). `fetch_clay_scan.py` downloads pinned 2K
files, checks source MD5 and records SHA256/provenance. The scan supplies colour,
roughness and physical height bump together; procedural hemisphere geometry is
removed in that comparison. The fine detail is intentionally scaled to a 0.10 m
repeat on the 1.2 m diorama specimen, rather than its real-world 1.3 m width.
The source photographs still determine art direction; a mud scan alone is not
a match to the sculpted relief model.

## Style authority correction

The user explicitly clarified that only the supplied images define the look.
The subsequent “large sandbox” wording is not an independent style brief and
must not drive material selection, container geometry, tool marks or sand-pile
forms. No sandbox-specific implementation was made. Searches for sand materials
were exploratory and are not an approved direction. The visual PRD now records
image-only authority and concrete observations from the original and ridge-level
images. All generic scan/procedural studies remain implementation experiments,
not replacement targets or evidence of visual acceptance.
