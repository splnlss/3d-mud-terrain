# 3D Mud Terrain — Product Requirements

> **Visual direction update:** [Visual style PRD](visual-style-prd.md) supersedes conflicting material restrictions and performance-first gate ordering. Visual fidelity and portable terrain assets are the primary acceptance gates. PlayCanvas is a preview adapter; geometry/material LOD governs runtime detail. The earlier performance figures are secondary optimisation targets.

## Problem Statement

San Luis Valley terrain is usually presented as a map or a geographically literal 3D scene. The desired experience is a real-time, explorable diorama that remains recognisably San Luis while looking like the hand-sculpted Relief Pfyffer model in [`reference/relief-pfyffer.png`](reference/relief-pfyffer.png). “Mud” describes the model's material, not a simulation.

## Solution

Bake real terrain and public imagery into a static, stylised 70 × 70 mi (~112 km) square centred on 37.20 N, 105.42 W. Stream it as OGC 3D Tiles with an implicit quadtree into a PlayCanvas viewer using the PlayCanvas renderer in 3DTilesRendererJS. Let visitors orbit an oblique camera over rounded clay-like relief, two-tone crust and granular faces, and flat painted-plaster water. Only water level, wetness, and water normal-scroll shader uniforms animate. A small debug panel exposes the height-remap curve, water level, and wetness.

## Users & use cases

- **Visitor:** orbit and zoom the diorama, recognise the Sangre de Cristo/Culebra range, Rio Grande, Culebra Creek, Sanchez Reservoir, Alamosa area, and agricultural pivot patterns.
- **Artist/developer:** tune the remap and wetness controls, compare a fixed-camera capture with the reference, and regenerate tiles reproducibly.
- **Mobile visitor:** get the same visual concept at native resolution on a mid-range phone within the performance budget.

## Style fidelity requirements

The attached Relief Pfyffer photograph is the authoritative style source. Every criterion below must be checked in fixed-camera screenshots at representative mountain, bank, valley-floor, and water views. The source depicts a photographed physical model, so compare material, shape, lighting, and composition; do not require pixel-level alignment between different geography.

| ID | Reference characteristic | Checkable criterion |
|---|---|---|
| S1 | Lumpy hand-pinched relief; stacked rounded clods; abrupt banks | At a fixed oblique mountain view, ridges have rounded, irregular lobes rather than knife-edge crests; at a fixed shoreline view, at least one steep bank meets a flat water sheet with a sharp boundary. |
| S2 | Smooth ochre/tan convex crust against dark grey-brown, pitted concavities and steep/shaded faces | Fixed views show both material families simultaneously. Crust placement follows curvature, slope, and sun aspect; the boundary is broken and clumpy, not a smooth contour band. Close crops show granular pits on dark faces and smoother crust on tops. |
| S3 | Pale grey-beige dust, strongest on upward flats | Dust is visible across terrain, stronger on upward-facing flats than vertical faces, and lowers overall saturation. |
| S4 | Flat, matte pale warm grey-beige painted water, sharp contact, dark rim, fine grain | Water surfaces are planar and visually matte in still frames, with a continuous sharp shoreline, faint darker rim, and fine texture. A subtle moving glint must not turn the surface into reflective glass. |
| S5 | Sparse rust-orange/red miniature flecks and thin pale path/twig strands | Close crops show occasional small flecks and pale strands; they stay sparse and do not read as mapped roads, buildings, or vegetation. |
| S6 | Warm low soft daylight, dark crevices, low oblique photographic view | A single fixed warm low sun and baked ambient occlusion make crevices distinctly darker; the default camera looks down and across without a horizon. Desktop depth-of-field/tilt-shift is optional. |
| S7 | Muted earth palette | Compare representative rendered swatches with image-picked reference swatches. Starting targets: ochre `#B08A55`, tan crust `#C2A57A`, dark granular `#4A4238`, mid grey-brown `#6E6250`, dust `#BDB3A0`, water `#EFE0C7` (warm grey-beige; see `reference/palette.json`). Record sampled values and review any material departure in side-by-side crops. |

## Functional requirements

1. Cover the complete square, including the New Mexico portion and roughly 15 km beyond Alamosa. The output must make the named landforms and waterways recognisable without requiring geographic precision.
2. Bake USGS 3DEP 10 m elevation (~11,200² source samples) through a tweakable, non-linear height-remap curve that boosts low-relief terraces, gorge rims, and banks while compressing high relief. Add low-amplitude rounded clod displacement before meshing.
3. Produce error-bounded Delatin adaptive TINs per LOD as GLBs with meshopt and `KHR_mesh_quantization`, skirts for tile seams, and an OGC 3D Tiles implicit quadtree. Static tiles must load from a CDN/object store without an application server.
4. Bake a per-tile ~256² KTX2 mask containing crust/granular blend, regraded satellite tonal variation, and dust amount. Use shared tiling 512² KTX2 crust and granular albedo/normal sets at two scales; no triplanar mapping. Bake strong ambient occlusion into vertex colours. Use no realtime shadows.
5. Derive Rio Grande, Culebra Creek, Sanchez Reservoir, and acequia water extent from NHD and Sentinel-2 NDWI. Fill DEM depressions to assign flat water surface heights; dilate channels into legible rivulets. Place flat water polygons as a second primitive in each relevant terrain GLB, aiming for two draw calls per tile.
6. Render water in one pass with a matte pale base, faint darker shoreline rim, fine grain, slight fresnel lift, subtle two-normal scrolling shimmer, tight sun glints, slow brightness pulse, and a soft wet band at the bank. Use no reflection or refraction buffers.
7. Use NAIP/Sentinel-2 only to derive tonal/wetness variation in the reference palette. Erase mapped roads and buildings. Keep pivot circles and field boundaries only as tonal/wetness variation; acequias remain thin channels.
8. Constrain orbit tilt and zoom to an oblique diorama view, exclude horizon views, and bound pan to the extent. Apply stylised mud falloff at the outer edges. Keep UI to camera controls and the debug panel.

## Performance budget

Measure on an iPhone 12 and a representative Snapdragon 7-series phone at each device's native display resolution, in a production build after loading the default view. Capture a 60-second orbit/pan/zoom trace and a separate cold-cache first load. Record device, browser, resolution, trace, and counters with each run.

| Budget | Acceptance criterion |
|---|---|
| Frame rate | Average at least 60 fps during the 60-second warmed trace on each target device, with at least 95% of frame times at or below 16.7 ms; report both fps and frame-time distribution. |
| GPU memory | Peak estimated GPU allocations for geometry, textures, and render targets under 150 MB during the trace. |
| First view transfer | Fewer than 5 MB compressed bytes transferred through the first meaningful terrain render from an empty cache, including viewer assets and tiles. |
| Draw calls | No more than 200 per rendered frame during the trace; target the 100–200 range or less. |

## Data sources & licensing constraints

- **USGS 3DEP 10 m DEM:** source elevation, including the New Mexico area.
- **NHD:** hydrography and named water bodies/channels.
- **NAIP and Sentinel-2:** imagery/NDWI inputs for tonal mask and water detection. Preserve source names, acquisition dates, URLs, and applicable notices in a bake manifest; verify reuse terms for each downloaded asset before publication.
- **Google Photorealistic 3D Tiles:** visual terrain reference only. Do not scrape, extract, transform, bake, distribute, or ship its geometry, imagery, textures, or derivatives. No runtime dependency on Google tiles.
- Download input data by script; do not commit source datasets. Generated detail textures must be authored offline, not cut from the Relief Pfyffer photograph. The photograph is a style reference, not a shipped texture.

## Out of scope

Geographic survey accuracy, globe rendering, ground-level exploration, runtime erosion/deformation/drying, mapped roads/buildings/vegetation, time-of-day controls, and a production UI beyond camera interaction and debug controls.

## Risks & open questions

- DEM, NHD, and imagery alignment or seasonal water differences may produce false or missing channels; inspect overlays and correct the bake inputs where needed.
- Remap and clod displacement can erase recognisable San Luis structure or create tile seams; compare landmarks and inspect all LOD transitions.
- KTX2/meshopt decoding, 3D Tiles implicit tiling, and two-primitive water GLBs may affect mobile transfer, draw calls, or memory; verify in the actual viewer early.
- **Open: villages/paths.** The reference contains miniature villages and paths, while the agreed product erases mapped roads and buildings. For now, use sparse non-geographic flecks and strands. Resolve whether any geographic human features should ever be represented before adding them.
- The palette values were sampled by eye in the design. Colour-pick the reference for calibrated swatches during the style pass; keep the image authoritative if sample values shift.

## Testing approach

- Each vertical slice must run from a reproducible bake command through GLB/tileset output to a visible browser view. Check its visual result before starting dependent work.
- Validate tileset metadata, tile bounds, LOD selection, GLB extensions/primitives, seams, and source-data provenance. Check named geography against independent DEM/hydrography overlays rather than Google-derived assets.
- Maintain fixed camera poses and identical viewport, lighting, exposure, and colour settings for baseline screenshots. Save side-by-side crops with the reference for mountain, bank, valley-floor, and water views; mark S1–S7 pass/fail with notes. Use image-picked swatches for S7 and check animated water both as a still and a short clip.
- Run the recorded mobile performance trace and cold-cache first-view test after feature additions and at final sign-off. A style match does not waive performance gates.
