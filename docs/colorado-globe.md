# Colorado crown

A separate single-resolution model set, with its own preview at `/colorado.html`.
The default view looks north: southwestern Colorado / San Juans on the left,
eastern Colorado / Front Range on the right. It is presented as a small Earth in
dark space: a wide, shallow cap with an atmosphere halo and a sliver of sunrise
behind it. The page shows only the title over the model, framed large like Earth seen from
orbit. The state outline is an optional guide, off by default.

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

- `colorado-crown.glb`: portable asset (110 MB): ordinary glTF materials, vertex colours and
  smooth normals; separate state border guide; one resolution, no tiles or runtime refinement.
- `colorado-crown-web.glb`: the same model with meshopt + KHR_mesh_quantization (29 MB),
  written by `node scripts/compress-colorado-glb.mjs`; the viewer loads this one.
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

## Mesh grid and elevation (revision 4)

The 1537 × 1537 mesh grid is uniform in *display* space. Each vertex is placed where it is
seen and samples the source map through the exact inverse of the display warp, so the
magnified state gets about twice the vertex density of the old source-space grid at the
same budget (1.85 M vertices). Elevation comes from a 6000 × 4650 USGS 3DEP export over just
the coverage circle (about 300 m per pixel; `source/dem-hires.tif`).

## Relief, snow and rivers

Elevation above 1,500 m is lifted 62× from a DEM blurred over 14 grid cells, and a finer band
(3-cell blur, 22×) brings out individual ranges and peaks: Front Range, Sawatch, San Juans,
Sangre de Cristo. A soft ceiling (`0.2 · tanh(h / 0.2)`) rounds the tallest crowns into
clay knuckles instead of spires. Snow uses original smoothed elevation.

Rivers follow the NHD centrelines exactly; each course is densified and warped into display
space, then cut at a constant on-screen width (5.2 km display for the Rio Grande, Arkansas,
Colorado and South Platte; 3.4 km for the others). The mud recipe's bank transitions are
scaled (×10) to suit these narrow channels and each bed is cut below its valley. Water colour
is the shared San Luis palette (`bake/style/water_palette.py`) in a warm silty tone.

The finish is matte earthen clay: GLB material roughness 0.95 for mud and snow, 0.6 for
rivers, specular level 0.2. Colour contains no baked lighting.

## Labels

`manifest.json` lists `places` (Ute Mountain Farm and Ranch, approximate; San Luis; Rocky
Ford; Denver) and `river_labels` (Colorado, Green, Yampa, San Juan, Rio Grande, Arkansas,
South Platte). River labels snap to a vertex of the mapped course; Colorado and Rio Grande
sit on their southern reaches (Moab; northern New Mexico) to read in the hero view. All are
projected through the same warp onto the displayed surface. Edit `PLACES` / `RIVER_LABELS`
and run `uv run python -m bake.style.colorado_globe --output data/colorado-globe --places-only`
to update them without re-baking.

The page has no buttons; review switches are URL parameters: `?view=top` (north-up map view),
`?outline=1` (state outline), `?places=0`, `?rivers=0`, `?stats=1` (frame time). Drag to orbit,
scroll to zoom, right-drag to pan.

## Performance

Measured in Chrome on this Mac at 1600 × 1000 CSS px, device pixel ratio 2: about 11 ms per
frame (≈ 92 fps) in both views, shadows on. MSAA is enabled only below a pixel ratio of 2
(cut 20 → 13 ms at 3200 × 2000); the web GLB loads in under 2 s from the dev server.
`?stats=1` shows frame time in the footer.

## Presentation layer (not in the GLB)

The atmosphere is scene staging only, identical in both renderers: a camera-facing halo one
sphere radius behind the globe centre, scaled so its limb lines up exactly in perspective.

- Broad glow: pale blue, brightest at the limb with a cubic fade to 1.7 sphere radii, and an
  amber lobe toward a low sunrise behind the crown (no sun disc).
- Limb band: a thin bright cyan band hugging the planet's horizon, like Earth from orbit.
- Both exist only behind the emerging planet: they are faded by the height of the sphere's
  tangent (horizon) point in each direction, so nothing glows down the planet's lower sides
  or below its base.

A weak warm back light comes from the sunrise direction.

- Blender: `presentation()` / `place_halo()` in `bake/style/blender_colorado_globe.py`.
- Browser: `src/colorado-atmosphere.ts`.

`portable-verification.json` lists the reimported GLB's materials and confirms the
halo and sun are not part of the asset.
