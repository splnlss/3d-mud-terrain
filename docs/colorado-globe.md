# Colorado crown

A separate single-resolution model set, with its own preview at `/colorado.html`.
The default view looks north: southwestern Colorado / San Juans on the left,
eastern Colorado / Front Range on the right. It is presented as a small Earth in
dark space: a wide, shallow cap with an atmosphere halo and a sliver of sunrise
behind it. The state outline is an optional guide, off by default.

## Build and inspect

```sh
# The current workspace links data/colorado-globe onto the external drive.
npm run bake:colorado
npm run dev -- --port 5197
# Open http://localhost:5197/colorado.html
npm run build:colorado
```

The site build includes the GLB. To use hosted assets instead, supply
`VITE_COLORADO_ROOT=https://…/colorado-globe` when building. No upload is performed.

The generated package is at
`/Volumes/TXX_Backup/DustnDivide/05_3D-tiles/colorado-globe/`:

- `colorado-crown.glb`: ordinary glTF materials, vertex colours and smooth normals;
  separate state border guide; one resolution, no tiles or runtime refinement.
- `colorado-crown.blend`: editable dense source and studio staging.
- `model.npz`, `geography.npz`, `border.json`: editable mesh arrays, true elevations,
  snow/channel fields and the geographic outline.
- `manifest.json`: projection, coverage, source checksums, shaping and river widths.
- `hero.png`, `overhead.png`, `detail.png`: source-scene renders (south-facing hero,
  north-up map check, Rio Grande border-crossing close-up).
- `portable-hero.png`, `portable-verification.json`, `gltf-validation.json`: independent
  GLB reimport render and Khronos validation (`node scripts/validate-colorado-glb.mjs`).
- `geography-review.png`: unbent north-up source elevation and widened rivers,
  state border and verified river crossings.
- `source/`: cached USGS float32 DEM, request metadata and NHD river geometry.

Fresh clones need to create their chosen output directory and link it into
`public/colorado-globe` before previewing. Generated models and source downloads
are intentionally excluded from git.

## Geography and artistic shaping

USGS 3DEP supplies raw elevation, resampled to a regional grid. USGS NHD
small-scale flowlines supply named rivers, including Colorado, Gunnison, Yampa,
San Juan, Animas, Dolores, Rio Grande, Arkansas and both Platte rivers. These are
mapped river routes, with no drawn replacement routes. The source checks verify:

| River | Colorado border crossing (longitude, latitude) |
|---|---|
| Rio Grande → New Mexico | −105.718801°, 37.000000° |
| Arkansas → Kansas | −102.050000°, 38.032390° |

The state boundary guide is the conventional geographic state envelope
(−109.05° to −102.05°, 37° to 41°), rather than cadastral survey detail.

A Colorado-centred azimuthal equidistant projection covers a circle enclosing all
four state corners plus 321,868.8 m (200 statute miles), with 2 km extra margin.
The map is then bent onto an artistic spherical cap. The cap is **not literal
Earth curvature**: it is the top 46° (half-angle) of a large sphere, about 15 % of
its diameter, so the model reads as a wide planet horizon rather than a ball.

## Display warp (revision 3)

Source coordinates, river routes and the border-crossing checks are never altered.
One continuous display transformation is applied to everything that is drawn:
terrain, channels, snow and the optional state outline.

1. A disk-preserving Möbius shift with focus (−0.14, +0.10) of the map radius moves
   the crown toward the state's west/north.
2. A monotone radial magnification, `tanh(2.2 r) / tanh(2.2)`, enlarges Colorado to
   about three quarters of the cap width and compresses the 200-mile buffer toward
   the rim. The eastern plains wrap onto the right shoulder; the Front Range sits
   right of centre and the San Juans left.
3. Relief fades to the ground over the outer fifth of the *displayed* radius, and
   heights are multiplied by `min(1, local warp scale)`, so the squeezed buffer keeps
   natural slopes and the cap meets the ground cleanly.

The warp has no cut, seam or foldover (tested). Distances are not uniform: this is
an authored overview composition, unsuitable for navigation or measurement.

## Relief, snow and rivers

Elevation above 1,500 m is exaggerated 62× after a 12-sample Gaussian rounding
pass, so plains and plateaus stay on the sphere and only the ranges rise; finer
variation is smoothed at 3 samples and exaggerated 16× to prevent needle peaks.
Snow uses original smoothed elevation, never the sphere height.

Rivers follow the NHD centrelines exactly. Major rivers (Rio Grande, Arkansas,
Colorado, South Platte) are 3.6 km wide in source terms and the other selected
rivers 2.3 km, down from 10 km / 6 km. Bank distance is measured to the mapped
polyline, the mud recipe's bank transitions are scaled (×10) to suit these narrow
channels, and each bed is cut below the valley the river actually follows. Water
colour is the shared San Luis palette (`bake/style/water_palette.py`) in a warm
silty tone, (0.81, 0.72, 0.58) × linear (0.42, 0.40, 0.36): clearly lighter than
the clay so rivers stay legible, without reading white.

The finish is matte earthen clay: GLB material roughness 0.95 for mud and snow,
0.6 for rivers, specular level 0.2. Colour contains no baked lighting.

## Presentation layer (not in the GLB)

The atmosphere and sun are scene staging only. Both renderers use the same formula:
a camera-facing halo one sphere radius behind the globe centre, brightest at the
limb with a cubic fade to 1.7 sphere radii, pale blue with an amber lobe toward the
sun, fading out toward the ground; a small emissive sun at source position
(0.30, 1.7, 0.44), low enough that the ridge hides most of it from the hero view;
and a weak warm back light from the same direction. Because the halo is behind the
terrain and the sun is a world-space object, the rim follows the silhouette and
the sun is occluded by terrain as the camera orbits.

- Blender: `presentation()` / `place_halo()` in `bake/style/blender_colorado_globe.py`.
- Browser: `src/colorado-atmosphere.ts`. Deep links: `?view=top`, `?outline=1`.

`portable-verification.json` lists the reimported GLB's materials and confirms the
halo and sun are not part of the asset.
