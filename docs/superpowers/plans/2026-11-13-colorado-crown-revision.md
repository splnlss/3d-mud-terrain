# Colorado Crown Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Colorado crown so the state spans most of the visible cap with its plains wrapped onto the right shoulder, rivers are narrow and San Luis-muddy, and the scene carries a restrained upper-horizon glow with a partly occluded sunrise.

**Architecture:** One continuous display warp (Möbius shift + monotone radial magnification) is shared by terrain, channel masks, snow and the border; it is retuned, and the rim taper moves into display space so the ground contact stays clean. Channels become a signed distance from the NHD centrelines with per-river half-widths, scaled so the shared mud recipe's bank transitions are proportionate to the new widths, and the channel bed follows the local valley height. Atmosphere and sun are scene presentation only: a radially offset copy of the terrain mesh carrying an additive limb-glow shader (Blender nodes and a PlayCanvas `ShaderMaterial`) plus a small emissive sun sphere and warm back light; nothing is baked into the GLB material.

**Tech Stack:** Python (numpy, scipy, rasterio, shapely), Blender 5.2 Cycles, PlayCanvas 2.24 (`ShaderMaterial`, GLSL), Vite, pytest.

**Spec:** `docs/handoffs/colorado-crown/PRD.md` (mockups in `docs/handoffs/colorado-crown/mockups/`). Supersedes `docs/superpowers/specs/2026-11-13-colorado-globe.md` where they conflict.

## Global Constraints

- Coverage: all of Colorado plus 200 statute miles (321,868.8 m) around the boundary; current radius ≈ 703,719 m is kept.
- Globe: spherical cap with one third of the sphere diameter above ground; `SPAN = 1.6`; one model resolution (1537), no LODs.
- Shared palette only: `WATER_LINEAR = (0.42, 0.40, 0.36)`, `WATER_ROUGHNESS = 0.22` from `bake/style/water_palette.py`; San Luis sets must keep working.
- Required crossings retained in source coordinates: Rio Grande −105.718800866°, 37.0°; Arkansas −102.05°, 38.032389737°.
- Mountains: rounded strongly exaggerated silhouette, no needle peaks; snow sparse at genuinely high elevation; the accepted mud recipe (`relief_study.style_surface`) is not reworked.
- Rivers: source full width start 3–4 km major / 1.8–2.4 km other, then judged by apparent width ≈ 35–50 % of the baseline (`hero-v1.png`) at the same camera scale.
- State footprint in a south-facing render: 75–90 % of visible cap width; east boundary/plains wrap to the right shoulder; south boundary crosses the lower foreground.
- Atmosphere/sun are separate from the terrain base colour and from the GLB; no large sun disc, flare, ground-contact halo, or exposure that washes out mud/snow/water.
- Generated assets and caches stay on `/Volumes/TXX_Backup/DustnDivide/05_3D-tiles/colorado-globe/` (`data/colorado-globe` symlink); `TMPDIR` points at its `work/tmp`. Nothing generated enters git. No deploy, merge or commit is requested by the handoff.
- Fresh evidence only: regenerate `hero.png`, `overhead.png`, `portable-hero.png`, `portable-verification.json`, `gltf-validation.json`, `dist-colorado/` after the final bake.

## Review Focus

1. Narrow channels at a 916 m grid pitch — a 1.8 km river is two cells wide; the mask must stay continuous (no beading) → Task 2 asserts continuity of the channel mask along a diagonal synthetic river.
2. Channel bed above the valley floor in mountain reaches (the old `datum` was a 5-cell blur) → Task 2 asserts bed ≤ neighbouring bank height for a V-valley.
3. Ragged silhouette at the ground contact after radial compression → Task 1 asserts the rim taper is evaluated in display space.
4. Glow or sun leaking into the portable asset → Task 6 asserts the GLB reimport lists only the two terrain materials and the border.
5. Water still reading white under Cycles because of exposure, not colour → Task 3 compares the rendered river luminance against the mud, with the San Luis `alamosa-pivots-rio-grande.jpg` as the reference.

---

### Task 1: Retune the display warp and move the rim taper into display space

**Files:**
- Modify: `bake/style/colorado_globe.py` (`display_map`, `cap_positions`, `author` taper, manifest `display_warp`)
- Test: `tests/test_colorado_globe.py`

**Interfaces:**
- Produces: module constants `WARP_FOCUS = (-.14, .10)`, `WARP_RADIAL = 2.0`; `display_map(x, y) -> (wx, wy)` unchanged signature; new `rim_taper(x, y) -> ndarray` in [0, 1] computed from display-space radius (1 at ≤ .88 R, 0 at R).

- [ ] **Step 1: Replace `test_state_fills_crown_and_eastern_plains_wrap_to_right_rim` with cap-space composition assertions**

```python
def test_state_spans_crown_with_plains_wrapped_to_right_shoulder():
    from bake.style.colorado_globe import display_map, cap_positions, SPAN
    x, y = project(np.array([-109.05, -105.2, -102.05, -107.6]), np.array([39., 39.3, 39., 37.7]))
    p = cap_positions(x, y, np.zeros(4)); half = SPAN / 2
    west, front, east, sanjuan = p[:, 0] / half
    assert east - west >= .75 * 2            # state covers ≥ 75 % of the cap width
    assert east >= .85 and west <= -.6       # both boundaries approach the shoulders
    assert .3 < front < .6 and sanjuan < 0   # Front Range right of centre, San Juans left
    assert east - front < front - west       # plains compressed relative to the mountain side
    angle = np.linspace(0, 2*np.pi, 200); radius = coverage_radius()
    bx, by = display_map(radius*np.cos(angle), radius*np.sin(angle))
    assert np.allclose(np.hypot(bx, by), radius)
```

- [ ] **Step 2: Add the rim-taper test**

```python
def test_rim_taper_follows_display_radius_not_source_radius():
    from bake.style.colorado_globe import rim_taper
    radius = coverage_radius()
    assert rim_taper(np.array([0.]), np.array([0.]))[0] == 1
    assert rim_taper(np.array([.86*radius]), np.array([0.]))[0] < .5   # display radius ≈ .98 R after compression
    assert rim_taper(np.array([radius]), np.array([0.]))[0] == 0
```

- [ ] **Step 3: Run both tests to verify they fail**

Run: `uv run pytest tests/test_colorado_globe.py -q -k "spans_crown or rim_taper"`
Expected: FAIL (`rim_taper` not defined; `front` assertion fails at 0.62 with the candidate focus).

- [ ] **Step 4: Implement**

In `bake/style/colorado_globe.py`: add `WARP_FOCUS`, `WARP_RADIAL` constants used by `display_map`; add `rim_taper(x, y)` = `1 - smoothstep(hypot(*display_map(x, y)), .88*R, R)`; in `author` replace `taper = 1-smoothstep(d, …)` with `rim_taper(x, y)`; write `display_warp` in the manifest from the constants and note the display-space taper. Keep `test_display_warp_has_no_foldovers_or_reordered_east_west_locations` passing.

- [ ] **Step 5: Run the file's tests**

Run: `uv run pytest tests/test_colorado_globe.py -q`
Expected: all pass.

### Task 2: Narrow mapped channels with proportionate banks and a valley-following bed

**Files:**
- Modify: `bake/style/colorado_globe.py` (`author`, new helpers, manifest `river_full_width_m`)
- Test: `tests/test_colorado_globe.py`

**Interfaces:**
- Produces: `RIVER_HALF_WIDTH_M = {'major': 1400, 'other': 900}` (full 2.8 km / 1.8 km — chosen so apparent width after ~2× crown magnification lands near 45 % of the 10 km / 6 km baseline; retune after Task 3's render if outside 35–50 %); `MAJOR_RIVERS = ['Rio Grande', 'Arkansas River', 'Colorado River', 'South Platte River']`; `BANK_SCALE = 10` (bank distance multiplier handed to `style_surface` so its ±2–4 mm transitions span ≈ 180 m outside to 350 m inside the edge); `channel_distance_m(shapes, n, radius) -> ndarray` signed metres from the channel edge (negative inside) built from rasterised centrelines, an EDT with indices and per-pixel half-widths; `channel_level(height, bank_m, px) -> ndarray` = sculpted height at the nearest channel-centre cell, smoothed 2 cells.

- [ ] **Step 1: Write the failing tests**

```python
def test_narrow_diagonal_channel_mask_is_continuous_and_two_cells_wide():
    from bake.style.colorado_globe import channel_distance_m
    from shapely.geometry import LineString
    n, radius = 129, 64_000.           # 1 km cells
    bank = channel_distance_m([(LineString([(-60_000, -60_000), (60_000, 60_000)]), 900)], n, radius)
    inside = bank < 0
    assert inside.sum() >= 2 * 120 * .9     # about two cells across every diagonal row
    rows = np.nonzero(inside.any(axis=1))[0]
    assert np.array_equal(rows, np.arange(rows[0], rows[-1] + 1))   # no gaps along the course
    assert abs(bank.min() + 900) < 600 and bank.max() > 50_000

def test_channel_bed_sits_below_valley_banks():
    from bake.style.colorado_globe import channel_level
    n = 101; rows = np.arange(n)[:, None]; height = np.abs(rows - 50) * .002 + .05   # V valley, floor at row 50
    bank = np.abs(rows - 50) * 1000. - 900 + np.zeros((n, n))
    level = channel_level(height, bank, 1000.)
    assert np.allclose(level[50], .05, atol=1e-3)
    assert np.all(level[50] <= height[49] + 1e-6)
```

- [ ] **Step 2: Run them to verify failure**

Run: `uv run pytest tests/test_colorado_globe.py -q -k "diagonal_channel or channel_bed"`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement in `bake/style/colorado_globe.py`**

`channel_distance_m` rasterises each centreline with `all_touched=True` and a per-feature half-width raster, EDT with `return_indices` (mirror of `relief_study.channel_distance`). In `author`: build `shapes` as `(LineString, half_width)` pairs, `bank_m = channel_distance_m(...)`, `bank = bank_m * scale`; call `style_surface(f, land, bank * BANK_SCALE, bank * BANK_SCALE, datum=datum, true_terrain=True)`; after styling apply `maps['height'] += (channel_level(height, bank_m, px) - datum) * maps['channel']` so the bed follows the valley; write `river_full_width_m` and `bank_scale` to the manifest.

- [ ] **Step 4: Run tests, then a 513-res scratch bake**

Run: `uv run pytest tests/test_colorado_globe.py -q`, then
`TMPDIR=$P/work/tmp uv run python -m bake.style.colorado_globe --output $P/work/preview --resolution 513` (`P=/Volumes/TXX_Backup/DustnDivide/05_3D-tiles/colorado-globe`).
Expected: tests pass; bake prints both crossings; `geography-review.png` shows thin continuous rivers.

### Task 3: Hero camera, exposure and water readability in the Blender scene

**Files:**
- Modify: `bake/style/blender_colorado_globe.py`

**Interfaces:**
- Produces: `--samples` default unchanged; new `--preview` flag renders at half size for iteration; perspective hero camera (`lens 45`, location `(0, -3.3, 1.05)`, target `(0, 0, .33)`, 1600×1000); overhead ortho unchanged; world shows a dark backdrop to camera rays only (`Light Path → Is Camera Ray` mixing `(.03, .026, .02)` against the existing lighting colour); state outline `bevel_depth = .002`.

- [ ] **Step 1: Render the Task-2 scratch package**

Run: `TMPDIR=$P/work/tmp blender --background --python-exit-code 1 --python bake/style/blender_colorado_globe.py -- --package $P/work/preview --samples 16 --preview`
Expected: `hero.png`, `overhead.png` written; read both.

- [ ] **Step 2: Judge against the PRD and references**

Check: state ≥ 75 % of cap width, east border on the right shoulder, San Juans left / Front Range right, no ragged rim; rivers thin, continuous, beige-grey not white (compare `docs/reviews/relief-tiles/alamosa-pivots-rio-grande.jpg`); measure mean sRGB of a river reach vs adjacent mud with PIL — river must stay under ~0.8 luminance and above the mud. If water clips, lower the key light energy / switch to `AgX - Base Contrast` before touching the palette; if rivers are >50 % of baseline apparent width, lower `RIVER_HALF_WIDTH_M` (Task 2) and re-bake; if the state misses the footprint, adjust `WARP_FOCUS`/`WARP_RADIAL` (Task 1) and re-bake. Record the final numbers for the report.

- [ ] **Step 3: Re-run `uv run pytest tests/test_colorado_globe.py -q`** after any constant change. Expected: pass.

### Task 4: Horizon glow and partly occluded sun in the Blender scene

**Files:**
- Modify: `bake/style/blender_colorado_globe.py`

**Interfaces:**
- Produces: `atmosphere_shell(obj, centre, offset=.035)` builds a non-exported mesh from the terrain vertices pushed radially from the sphere centre `(0, 0, -sphere/3)`; its material = Add Shader(Transparent, Emission) where Emission = pale blue `(.45, .66, 1.0)` × `(1 - |dot(radial, incoming)|)^5` × `smoothstep(z, .12, .40)` × `GLOW` + amber `(1.0, .55, .22)` × `max(dot(radial, SUN_DIR), 0)^40` × `HALO`; `visible_shadow/diffuse/glossy = False`. `sun_sphere` radius `.02` at `SUN_POS = (.28, 1.7, .60)` with Emission `(1, .62, .3)` strength 40; a `SUN` lamp (`type='SUN'`, energy 1.2, colour `(1, .72, .45)`) aimed from `SUN_POS` toward the origin as back light. Constants exposed at module top: `GLOW = .9`, `HALO = 1.4`.

- [ ] **Step 1: Implement, keeping the shell and sun out of the GLB selection**

Only `obj` (terrain) and `border` are selected for `export_scene.gltf`; the shell, sun and lamps are created after the export call.

- [ ] **Step 2: Preview render and judge**

Run the Task 3 Step 1 command. Expected: thin cool rim along the upper silhouette including the mountain outline, fading out before the ground ring; small warm sliver slightly right of centre mostly hidden by the ridge; mud, snow and rivers unchanged in exposure. Tune `GLOW`, `HALO`, `SUN_POS` only.

- [ ] **Step 3: Orbit coherence check**

Add an `--orbit-check` option rendering the hero from yaw ±35° at preview size; expected: the rim follows the silhouette and the sun disappears/reappears behind terrain rather than staying screen-fixed. Delete the two check images after review or keep in `work/`.

### Task 5: Viewer presentation: atmosphere shell, sun, hero framing

**Files:**
- Modify: `src/colorado.ts`, `colorado.html` (footer copy only)
- Create: `src/colorado-atmosphere.ts`
- Test: manual browser check via Playwright screenshot script in `work/` (not committed)

**Interfaces:**
- Produces: `createAtmosphere(app, terrain: Entity, options: { centre: Vec3, sunDir: Vec3 }) -> Entity` in `src/colorado-atmosphere.ts`: clones the terrain render component's mesh instances with a `ShaderMaterial` (`uniqueName: 'colorado-atmosphere'`, GLSL vertex offsets `vertex_position` radially by `.035`, fragment reproduces the Task 4 formula in display-referred colour; `blendType = BLEND_ADDITIVE`, `depthWrite = false`), and adds a `sun` sphere entity (StandardMaterial `emissive (1, .62, .3)`, `emissiveIntensity 3`, `diffuse` black) at `SUN_POS` mapped to GLB axes `(x, z, -y)` = `(.28, .60, -1.7)`; a second directional light `warm back light` intensity .5 from the sun direction. Hero preset: `pitch .3`, `height .3`, `distance 2.55·aspect factor`.

- [ ] **Step 1: Implement and type-check**

Run: `npx tsc --noEmit`. Expected: no errors.

- [ ] **Step 2: Serve the scratch package and screenshot**

Run: `VITE_COLORADO_ROOT=/colorado-globe/work/preview npm run dev -- --port 5197` is not needed — the preview package lives under `public/colorado-globe/work/preview`; open `http://localhost:5197/colorado.html?root=…` only if a `root` query is added; otherwise temporarily point `VITE_COLORADO_ROOT` at `/colorado-globe/work/preview` in the dev command: `VITE_COLORADO_ROOT=/colorado-globe/work/preview npx vite --port 5197`. Screenshot hero and map views with Playwright, toggle the outline, assert the download link ends in `colorado-crown.glb`.
Expected: glow at the upper limb, sun sliver right of centre, rivers beige-grey, outline toggles, map view shows north-up state with plains compressed to the east.

### Task 6: Final rebuild, independent verification, docs and manifest

**Files:**
- Create: `scripts/validate-colorado-glb.mjs` (gltf-validator on `data/colorado-globe/colorado-crown.glb`, writes `gltf-validation.json` beside it, exits 1 on errors)
- Modify: `scripts/build-colorado-site.sh` (run the validator before copying), `docs/colorado-globe.md`, `README.md` (river/width sentence), `package.json` if a script alias is added
- Test: `tests/test_colorado_globe.py` manifest keys

- [ ] **Step 1: Full bake with `TMPDIR` on the external drive**

Run: `export TMPDIR=$P/work/tmp; npm run bake:colorado` (1537 resolution, 48 samples).
Expected: `model.npz`, `geography.npz`, `border.json`, `manifest.json`, `colorado-crown.glb`, `colorado-crown.blend`, `hero.png`, `overhead.png`, `geography-review.png` all newer than the plan; manifest `river_full_width_m` = final values, `display_warp` = final values, `bank_scale`, `presentation` block describing glow/sun as scene-only.

- [ ] **Step 2: Independent GLB reimport**

Run: `blender --background --python-exit-code 1 --python bake/style/blender_colorado_globe.py -- --package data/colorado-globe --verify`
Expected: `portable-hero.png` matches `hero.png` (same framing, glow and sun present because the verify scene adds the same presentation objects); `portable-verification.json` materials = `['Warm mud and dark clumps', 'Mapped narrow rivers', 'Colorado boundary']`-equivalent and no atmosphere material.

- [ ] **Step 3: Validate, test, build**

Run: `node scripts/validate-colorado-glb.mjs data/colorado-globe && npm test && npm run build:colorado`
Expected: `numErrors: 0`; pytest and node tests pass (report any pre-existing failures verbatim); `dist-colorado/colorado-globe/colorado-crown.glb` copied.

- [ ] **Step 4: Browser check on the final asset**

Run: `npx vite --port 5197`; Playwright screenshots of horizon and map views, outline toggle, download link.
Expected: as Task 5 Step 2, with the final 1537 asset.

- [ ] **Step 5: Documentation**

Update `docs/colorado-globe.md`: widths (final km), warp constants, bank scale, bed rule, presentation layer (what is viewer/Blender-only), evidence list; mark revision 2 text as superseded. README sentence: "mapped narrow rivers". Add a river close-up render (`detail.png`) to the Blender views for acceptance.
