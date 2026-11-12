# 3D Mud Terrain — Design

A stylised, real-time diorama of the San Luis Valley (Colorado), streamed as OGC 3D
Tiles. Real terrain drives the form; satellite imagery and Google 3D Tiles are terrain
reference only. **The reference image (`docs/reference/relief-pfyffer.png`) is the
authoritative style source and must be matched closely** — not "generic mud".

## Style source

The reference is a close-up of the **Relief Pfyffer** (Gletschergarten Lucerne), a
hand-sculpted 18th-century topographic relief model of central Switzerland. What reads
as "mud" is a physical model: mountains hand-modelled in clay/wax/sand, dusty with age,
lakes as flat painted sheets. The target is *that physical model, photographed close and
low* — applied to San Luis Valley terrain.

Characteristics to reproduce (all are acceptance criteria for the look):

- **Form:** lumpy, hand-pinched, slightly blobby relief; ridges read as stacked rounded
  clods, not sharp crests. Steep banks drop abruptly to water.
- **Two-tone surface:** smoother **ochre/tan crust** on convex tops, ridges and
  sun-facing slopes; **dark grey-brown granular, pitted, crumbly texture** (like packed
  charcoal or coarse wet sand) in concavities, steep faces and shaded slopes. The split
  is driven by curvature, slope and aspect, with a broken, clumpy boundary.
- **Dust layer:** a pale grey-beige dusty veil over everything, strongest on
  upward-facing flats. Lowers saturation overall.
- **Water:** flat, matte, pale warm grey-beige sheets, like painted plaster.
  Sharp contact line with the land, a faint darker rim, very fine surface texture.
  Shimmer (a project requirement) stays subtle enough not to break this matte read.
- **Micro-detail:** sparse tiny rust-orange/red flecks (miniature trees and houses on
  the model) and occasional thin pale lines (paths, twig-like strands) on the surface.
- **Lighting and camera:** warm, low-angle, soft daylight; strong ambient occlusion in
  crevices; oblique view looking down and across; shallow depth of field optional.
- **Palette** (sampled by eye; confirm by colour-picking the image): ochre `#B08A55`,
  tan crust `#C2A57A`, dark granular `#4A4238`, mid grey-brown `#6E6250`, dust
  `#BDB3A0`, water `#EFE0C7` (warm grey-beige; sampled from the photograph).

## Goals

- Recognisably San Luis — Sangre de Cristo / Culebra range, Rio Grande, Culebra Creek,
  Sanchez Reservoir, Alamosa, pivot circles — rendered as a close-up of the Relief Pfyffer model.
- Matte, pale painted-plaster water with a subtle shimmer.
- Runs at 60 fps on a mid-range phone.

## Non-goals

- Geographic accuracy, globe rendering, ground-level exploration.
- Runtime simulation (erosion, deformation, drying). Terrain is static.
- Roads, buildings, vegetation.

## Decisions

| Area | Decision |
|---|---|
| Product | Real-time interactive web viewer. "Mud" = material only. |
| Dynamics | Static geometry. Only shader uniforms animate (water level, wetness, normal scroll). |
| Extent | 70 × 70 mi (~112 km) square centred on San Luis (37.20 N, 105.42 W); ~15 km past Alamosa, well past Rio Grande and Culebra. Stylised mud falloff at the edges. |
| Elevation | USGS 3DEP 10 m DEM (~11,200² samples). Covers the NM portion. |
| Scale | Diorama/macro read. Non-linear height remap (tweakable curve): boost low relief (terraces, gorge rim, banks), compress high relief. |
| Reference | Google Photorealistic 3D Tiles: eyeball reference only — nothing extracted or shipped (ToS). NAIP / Sentinel-2 (public domain) baked into a macro mask, re-graded into the photo palette. |
| Water extent | NHD hydrography (Rio Grande, Culebra Creek, Sanchez Reservoir, acequias) + Sentinel-2 NDWI. DEM depression-fill gives each body a flat surface height. Mask dilated so channels read as broad rivulets. |
| Human features | Roads/buildings erased. Pivot circles and field boundaries survive only as tonal/wetness variation. Acequias kept as thin water channels. |
| Delivery | OGC 3D Tiles, implicit quadtree, static files on a CDN/object store. No server. |
| Runtime | PlayCanvas + 3DTilesRendererJS (PlayCanvas renderer) (NASA-AMMOS); custom mud and water materials swapped in on tile load. |
| Meshing | Custom bake: GDAL heightmap → height remap → Delatin adaptive TIN per LOD (error-bounded) → GLB with meshopt + KHR_mesh_quantization, skirts for cracks. |
| Water geometry | Second primitive inside each terrain GLB: flat polygons at water surface height. 2 draw calls per tile. |
| Camera | Constrained oblique orbit: clamped zoom and tilt, no horizon views, pan bounded to extent. Tilt-shift blur on desktop only. |
| Tooling | Python bake (rasterio/GDAL, pydelatin, numpy) + gltf-transform CLI. Source data downloaded by script, never committed. |

## Performance budget

- 60 fps at native res on iPhone 12 / Snapdragon 7-series class.
- < 150 MB GPU memory, < 5 MB to first view, ≤ 100–200 draw calls.

## Terrain material (Relief Pfyffer look)

- **Per-tile bake:** one ~256² KTX2 texture packing: crust-vs-granular blend factor
  (from curvature + slope + aspect, with clumpy noise), satellite-derived tonal variation
  re-graded into the palette, and dust amount.
- **Shared:** two tiling 512² KTX2 sets — smooth ochre crust and dark pitted granular —
  each albedo + normal, sampled at two scales. No triplanar.
- **Lumpy form:** bake adds low-amplitude rounded "clod" displacement to the heightmap
  before meshing so ridges read hand-pinched.
- **Lighting:** single warm low directional sun; strong AO baked into vertex colours;
  no realtime shadows.
- **Micro-detail:** sparse rust-orange flecks and thin pale strands via the detail
  texture or a cheap hash in-shader.

## Water shader

- Matte pale warm grey-beige base (painted-plaster read), faint darker rim at the
  shoreline, very fine surface grain, slight fresnel lift.
- Shimmer: two scrolling low-frequency noise normals + tight sun specular → subtle drifting
  glints; slow brightness pulse; soft wet band brightening at the shoreline.
- Single pass. No reflection or refraction buffers.

## Assumed defaults (not explicitly discussed)

- Fixed warm low-angle sun matching the reference; no time-of-day control.
- Detail textures are generated (procedurally authored offline) to match the reference,
  not cut from the reference photo.
- Open: the reference shows tiny model villages/paths. Current decision erases roads and
  buildings; sparse flecks/strands give the same texture without real data.
- No UI beyond the camera, except a debug panel (height-remap curve, water level, wetness).
