# Relief process: from a map square to a clay-model tile

Status 2026-11-13: runs end to end on one 2 km tile (Culebra Creek). The look is a
user-approved direction, not final acceptance. Scaling items at the bottom are open.

One tile = one config = one run of `scripts/relief_pipeline.sh`. Every stage is a
single command, reads only the previous stages' files, and can be rerun alone.

```sh
# all stages for a tile (GOOGLE=1 adds Google imagery and 3D Tiles terrain)
GOOGLE=1 scripts/relief_pipeline.sh configs/<tile>.json <name>
# one stage
scripts/relief_pipeline.sh configs/<tile>.json <name> author
# the existing tile, whose source package predates the naming rule
PACKAGE=data/style-patch scripts/relief_pipeline.sh configs/style-patch.json relief-patch author check render
```

## Stages

| Stage | Command behind it | Reads | Writes | Review before moving on |
|---|---|---|---|---|
| `source` | `bake.style --config` | regional DEM GeoTIFF, NHD hydrography, tile centre and size | `data/<name>-package/`: DEM window, mapped river, manifest | manifest hashes match the config |
| `fetch` | `bake.style.fields`, `bake.style.google_tiles` | tile square from the manifest | `reference/`: NAIP colour and infrared, roads (OSM + USGS + TIGER), Google satellite and `google-surface.npy` | images cover the square, no error pages |
| `author` | `bake.style.relief_patch` | package + `reference/` | `surface.npz`, height/colour/roughness PNGs, `water-mask.png`, `water-flow.png`, `road.png`, manifest | — |
| `check` | `bake.style.source_check` | package + `reference/` | `naip-overlay.jpg`, `naip-fields.jpg` | **rivers, tributaries, roads and fields sit on the photo** |
| `render` | `blender_relief_study.py` | `surface.npz` | overhead, elevated and creek views with settings JSON | compare with the aerial photo and style references |
| `boards` | `scripts/relief_boards.py` | renders | side-by-side boards in `docs/reviews/` | currently wired to the two existing sets only |

## What each feature is derived from

| Feature | Source | Rule |
|---|---|---|
| Ground shape | USGS 10 m DEM, plus Google 3D Tiles (2 m level, about 3 m vertex spacing) | DEM is the bare-earth base. Google adds finer shape after a 25 m opening removes trees; under broad forest the DEM is used alone. Smoothed 12 m before any exaggeration. |
| River | NHD centreline | Drawn about 12 m wide. |
| Tributaries | drainage computed on the ground grid | Shifted up to 55 m onto the tree line seen in imagery; run to the river; kept only where incised or tree-lined; gaps over 250 m left open. |
| Ponds | NHD waterbodies | Level silt. |
| Dark crust | NAIP darkness and woody cover (infrared + texture) | 3 m blur, slight noise. |
| Fields | NAIP infrared parcels | Level combed ground; rows follow the photo; near-circles become centre pivots. |
| Roads | OSM, then USGS and TIGER stretches OSM lacks | Scored ochre grooves with a lip. |
| Water surface | channel mask and source water level | Separate `Water` object and material. Change it with `--water-colour r,g,b --water-roughness x`, or drive an engine shader from `water-mask.png` (R mask, G bank distance) and `water-flow.png` (RG downstream direction). |
| Clay, nodules, cracks | `relief_study.style_surface` | Shared with the calibration specimen. |

## Regional tileset (3D Tiles)

The whole 112.64 km square (36.69–37.71° N, 106.06–104.78° W: Alamosa, the Rio Grande,
San Luis, Culebra Peak) is baked as a quadtree of clay-model tiles.

```sh
uv run python -m bake.style.relief_tiles --output data/relief-tiles --levels 0-4            # whole region
uv run python -m bake.style.relief_tiles --output data/relief-tiles --levels 5-6 --refine=-105.27,37.18,1   # extra detail near a point
uv run python -m bake.style.relief_tiles --output data/relief-tiles --tileset               # rewrite tileset.json only
npx vite, then open /relief.html                                                            # preview (public/relief links to data/relief-tiles)
node scripts/relief-shot.mjs "http://localhost:5173/relief.html" shot.png                   # headless capture
```

### San Luis walkable sample

`relief-tiles-sample` on the external drive: whole region to level 3, 20 km around San Luis to level 6, 5 km to level 7
(script: `<set>/work/sample-bake.sh`). After baking, write the index and the ground map the walking camera uses:

```sh
uv run python -m bake.style.relief_tiles --output <set> --tileset
uv run python -m bake.style.relief_tiles --output <set> --ground          # ground.bin: finest mesh heights, 10 m cells
uv run python -m bake.style.detail_material --output <set>/detail         # repeating close-range dirt detail (6.875 m square)
```

Rules for this set: one exaggeration (×1.25); the mesh is the real terrain plus ground-anchored canopy lumps on trees and brush,
identical at every level; all other clay detail is shading. Below about 12 m mesh spacing, stream beds dip and buildings stand.
Each tile peaks at about 3.5 GB of memory while baking.

### Irrigation ditches and acequias

```sh
uv run python -m bake.style.ditches --output <set>/ditches
```

writes `ditches.geojson` (2,413 km of NHD canal and ditch lines, with name, Colorado water-right number and earliest
appropriation date where a headgate is within 400 m), `headgates.geojson` (924 ditch headgates from Colorado DWR),
and review maps. Acequias are flagged approximately: a Costilla or Conejos county ditch whose first right predates 1880,
or whose name says acequia; the flag spreads along segments sharing a name. New Mexico ditches have NHD names only.
The preview drapes them on the ground map (button or D; blue ditches, red acequias) inside the 44 km walkable square.

### Published sample and static site

The sample is uploaded to Cloudflare R2, bucket `demo-assets`, prefix `05_3D-tiles/san-luis-relief-sample/`
(`rclone copy <set> R2:demo-assets/05_3D-tiles/san-luis-relief-sample --files-from <set>/work/upload-list.txt`).
Public entry point (the bucket name is not part of the public path), CORS open:
`https://pub-dd92ae5131ec49f1bbd411b51a858249.r2.dev/05_3D-tiles/san-luis-relief-sample/tileset.json`

```sh
VITE_RELIEF_BASE=https://pub-dd92ae5131ec49f1bbd411b51a858249.r2.dev/05_3D-tiles/san-luis-relief-sample scripts/build-relief-site.sh
```

writes `dist-relief/`, a 3.8 MB static site that reads the tiles from the bucket; host it anywhere.

The preview has three views at one shared camera: new relief, old relief, and Google Photorealistic 3D Tiles (true scale).
The Google view needs the Maps key in the dev server's environment (it is never written to disk):

```sh
doppler run -p misc_projects -c dev -- sh -c 'VITE_GOOGLE_MAPS_KEY=$NEXT_PUBLIC_GOOGLE_MAPS_TOKEN exec npx vite --port 5199 --strictPort'
```

It also needs Google's Draco decoder under `public/wasm/draco/` (from gstatic.com/draco/versioned/decoders/1.5.7; ignored by git).

Tiles and the bake cache live on the external drive at `/Volumes/TXX_Backup/DustnDivide/05_3D-tiles/relief-tiles`;
`data/relief-tiles` is a symlink to it, so every command above works unchanged while the drive is mounted.
Keep processing off the local drive: run bakes with `TMPDIR=<set>/work/tmp` so encoder scratch files go to the external drive,
and use at most 5 workers; more than that pushes the machine into swap, which lives on the local drive.

| Item | Rule |
|---|---|
| Tree | Level L has 4^L tiles of 112.64 km / 2^L. A tile refines only when all four children are baked (`REPLACE`). |
| Tile | Authored as its own 1.6 m clay model at 1537² samples, so each zoom level reads as sculpted relief. Exported as a 193² mesh with a skirt, plus base colour, normal and roughness textures. |
| Coordinates | Content is metres east/north/up of the region centre; `root.transform` places it in Earth-centred coordinates (EPSG:4978). Bounding volumes are boxes. Heights are ellipsoidal (NAVD88 − 16.2 m), exaggerated ×2 above 2200 m; both are recorded in `tileset.json` extras. |
| Seams | Noise and nodules are anchored to a global lattice and each tile is authored with a halo, so neighbours at one level agree along their edge. Different levels are different sculptures: detail changes when a tile refines. |
| Rivers | NHD lines chosen by their map-scale attribute per level, each at least wide enough to read; canals from level 3; lakes and reservoirs as level silt. DEM-derived tributaries and tree-line snapping are **not** used in tiles yet. |
| Centre pivots | Found once for the region by their circular outline on a 20 m NAIP mosaic (`region-pivots.npy`), drawn as combed discs at every level. |
| Other fields | Rectangular parcels read per tile from level 4 down (imagery finer than 8 m). |
| Homes | OpenStreetMap building centres as small raised blocks from level 2 down. Rural homes missing from OpenStreetMap are missing here. |
| Roads | OpenStreetMap: highways at every level, tertiary from 2, local from 3, service and tracks from 4. |
| Tone | NAIP darkness and green-and-dark cover. New Mexico imagery (south of 37° N) is matched to Colorado's tone along the state line. |
| Water for shaders | Baked into colour and roughness by default. Each material's `extras` names two extra textures: water mask / bank distance / road, and downstream flow direction. |

## Applying it to a larger area: what works and what does not yet

Works now: any 2 km square inside the regional DEM and NHD files, by writing a
config with a new centre. Measured on this machine: fetch about 3 min with Google
(4,753 tiles, 77 MB), author about 1 min, each render about 30 s.

Open before a multi-tile run:

1. **Tile seams.** Solved within a level (world-anchored noise plus halo). Still open between levels, and for per-tile field detection at tile borders.
2. **Drainage across borders.** Flow is computed inside one tile; a tributary
   entering from a neighbour starts cold. Needs a halo of source data (about 500 m).
3. **Tile driver.** `bake.style.relief_tiles` bakes any level range in parallel and resumes where it stopped. About 85 s per tile on six workers.
4. **Google volume.** The full 112 km extent at the 2 m level is roughly 15 million
   tile requests. Use Google only on chosen tiles, or the 8 m level elsewhere.
   Google content is a local working copy and is not committed.
5. **Thresholds tuned on one scene.** Field, woody-cover and incision thresholds
   were set on a July NAIP image of foothill ranchland. Expect retuning on
   irrigated valley floor (centre pivots are untested on real data) and high forest.
6. **Scale.** 1:1250 with 0.5 mm samples suits a 2 km tile; a regional view needs
   a coarser level derived from these tiles, which does not exist yet.
8. **Runtime memory.** Each tile carries five uncompressed 1537² textures (about 60 MB on the GPU). A 900 MB cache holds about 15 tiles; close views need `?cacheMB=4000` until textures are compressed (KTX2) and the two shader-input textures are loaded on demand.
9. **Close-up landforms.** At levels 5–6 the ×2 vertical gain makes foothills read as steep cones under real-time light.
7. **Export.** The regional tileset is plain GLB with JPEG/PNG textures at about 6.5 MB per tile; no KTX2 or mesh compression yet. The detailed single-tile pipeline above (Google terrain, DEM tributaries) is not yet merged into the tile baker.
