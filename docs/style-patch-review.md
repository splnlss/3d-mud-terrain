# Sculpted reference patch: work in progress

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
