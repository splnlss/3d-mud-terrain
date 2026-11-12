# San Luis relief

A browser diorama of a **70 × 70 mile square centred on San Luis, Colorado**.
Real USGS elevation supplies the geography; the [reference photograph](docs/reference/relief-pfyffer.png)
supplies the rounded, dusty, two-tone physical-model style. The viewer uses
**PlayCanvas**, WebGL2 and the PlayCanvas renderer in NASA-AMMOS 3DTilesRendererJS.

## Run locally

Requires Node.js **22.18+**, npm, and [uv](https://docs.astral.sh/uv/).
uv manages Python 3.12 and the bake dependencies.

```sh
npm ci
npm run setup:bake
npm run bake:scene
npm run dev -- --port 20000
```

Open **http://localhost:20000**. Drag to orbit, scroll/pinch to zoom, and
right-drag, shift-drag or use two fingers to pan. Reset view returns to the overview.
Study notes contains the debug controls and live counters.

The first scene bake downloads public DEM, imagery and hydrography into `data/`.
Allow several minutes and at least 2 GB of free disk space. A rebake stages a
complete replacement beside the previous output before switching it into place. Subsequent bakes reuse
the local inputs. Source datasets, generated tiles, decoders, build output and
local tools are ignored by git.

`setup:bake` prepares KTX-Software 4.4.2 inside `data/tools/` on Apple Silicon macOS,
verifies its package checksum, and downloads and verifies the matching PlayCanvas
Basis decoder against pinned SHA-256 digests. A bake preflights tools before reading
data and records the actual Node, KTX and glTF-transform versions.
On other platforms, put [KTX-Software 4.4.2](https://github.com/KhronosGroup/KTX-Software/releases/tag/v4.4.2)
(`toktx`) on PATH before running setup. No system-wide install is performed by the script.

## Bake stages

| Command | Result |
|---|---|
| `npm run bake` | A real 12 km DEM patch and one diagnostic GLB tile. |
| `npm run bake:full` | Full 112.64 km extent, five LODs, implicit quadtree, meshopt geometry. |
| `npm run bake:style` | Rounded relief, height remap, KTX2 material masks and shared details. |
| `npm run bake:scene` | Styled extent with mapped water and satellite field tones. |

Custom shaping is available through the same CLI:

```sh
uv run python -m bake --full --style --material --water --imagery --compress \
  --gain 5 --knee 800 --clods 60 --rounding 60 --edge-width 5500
```

The curve and clod changes are **offline**; rebuild and reload after editing them.
The wetness slider affects shading. The water slider makes a small local level
adjustment within the baked footprint; it does not simulate regional flooding.
Study notes also provides fixed views of the range, gorge, reservoir and fields,
and a 60-second performance recorder that downloads frame timings and memory
estimates. Orbit, pan and zoom throughout a capture on each target phone.

Generated assets live in `public/terrain/`. `manifest.json` records source URLs,
imagery acquisition dates, source identities/checksums, sample grid, style parameters and
mesh statistics. `tileset.json` references GLBs and a single binary implicit subtree.
Inputs use a common UTM 13N grid; output uses local metre coordinates near the
origin. The viewer converts the 3D Tiles Z-up frame to PlayCanvas Y-up.

## Verify and build

```sh
npm test
npm run validate:assets
npm run build
npm run preview -- --port 20001
```

Publish the generated `dist/` directory to a static host. No API server or account
is needed by visitors. Configure a subdirectory deployment through Vite's `base`
setting; all application asset URLs respect it. Enable gzip/Brotli for JavaScript,
CSS, JSON and WASM at the host; transfer figures use compressed HTTP responses.
Publish each complete release under a versioned base path, or invalidate terrain,
masks, manifests and decoders together when replacing unversioned URLs.

Tests cover geometry winding, coordinate orientation, bounds, missing elevation,
reproducibility, implicit availability, LOD grid division, height shaping, material
placement, sparse marks, water islands/seams, and orbit limits. Real-device mobile
performance and visual sign-off remain separate gates; desktop counters alone
do not establish them.

## Source and requirements

- [Visual style PRD — quality first, engine-agnostic assets](docs/visual-style-prd.md)
- [Sculpted reference patch implementation plan](docs/superpowers/plans/2026-11-12-sculpted-reference-patch.md)
- [Original PRD](docs/prd.md), [design](docs/design.md), [task sequence](docs/tickets/README.md)
- [Implementation progress and limitations](docs/progress.md)
- [Validation evidence and remaining gates](docs/validation.md)
- [PlayCanvas 3D Tiles integration](https://developer.playcanvas.com/user-manual/engine/libraries/3d-tiles/)
- [USGS 3DEP staged DEMs](https://www.usgs.gov/3d-elevation-program)
- [USGS NHD](https://www.usgs.gov/national-hydrography/national-hydrography-dataset)
- [Sentinel-2 public COG catalog](https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a)

Satellite reflectance is reduced to muted tonal variation and NDWI. Google 3D
Tiles are visual reference only and do not enter the bake or runtime. The style
photograph is not used as a texture.

### Portable sculpted reference patch

`npm run bake:patch` windows the selected 2 km Culebra Creek foothill reach from
cached regional DEM/NHD inputs, verifies their pinned hashes, and writes
`data/style-patch/manifest.json`, source arrays, clipped water and review overlays.
Run the regional data bake first if the cached inputs are absent. Source masters
and the package contract are independent of the preview engine. Generated packages
stay under the ignored `data/` directory. See the [patch plan](docs/superpowers/plans/2026-11-12-sculpted-reference-patch.md).
