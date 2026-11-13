# Relief style on the real Culebra Creek patch (2026-11-12)

**Not visually accepted.** The specimen recipe driven by the real 2 km patch:
`data/style-patch/source/dem.npy` and `water.geojson`. Sharp captures only;
depth of field is deferred by user decision.

| Board | Reference | Render |
|---|---|---|
| [Along the creek](compare-creek.jpg) | 04 | [colour](creek-sharp.jpg), [neutral clay](creek-clay-sharp.jpg) |
| [Elevated](compare-elevated.jpg) | 01 | [elevated](elevated-sharp.jpg) |
| [Overhead](compare-overhead.jpg) | 03 | [overhead](overhead-sharp.jpg), north up |
| [Aerial photo beside render](compare-aerial.jpg) | NAIP | same square; the render camera is slightly tilted |

```sh
GOOGLE=1 PACKAGE=data/style-patch scripts/relief_pipeline.sh configs/style-patch.json relief-patch fetch author check render boards
```

Stages and scaling limits: [relief process](../../relief-process.md).

## What follows the source

Checked against USGS NAIP aerial imagery of the same 2 km square:
[overlay](source-check-overlay.jpg) (cyan creek, yellow gullies, magenta ponds, orange roads).
Google satellite tiles are fetched to `data/relief-patch/reference/` with the key held
in Doppler (`misc_projects/dev`), as a local cross-check only: this square's Google
mosaic is an autumn scene with a seam, so NAIP drives tone. Google imagery stays out
of the repository. Google 3D Tiles (2 m level) add finer ground shape on top of the USGS DEM;
trees are removed from Google's surface first.

- The wide channel is the mapped NHD Culebra Creek centreline.
- Tributaries start from DEM drainage lines (D8, at least 500 contributing cells),
  then shift up to 55 m sideways onto the strip of trees and brush the imagery shows
  along the real watercourse; a 10 m DEM places small creeks tens of metres off.
  Each runs until it meets the river centreline, so creek and river join.
  A reach is kept where the DEM is incised by 1 m or the imagery shows a tree line;
  unsupported gaps over 250 m are left out rather than ruled straight across open ground.
- The two pools south of the creek are mapped NHD waterbodies.
- **Fields:** cultivated parcels are read from NAIP colour-infrared imagery
  ([parcels found](source-check-fields.jpg)). Each becomes level combed ground with
  a boundary groove; rows run the way the mowing or tilling lines run in the photo.
  Near-circular parcels get concentric rows (centre pivots); this square has none.
- **Light and dark:** dark crust follows what is dark or woody in the photo (6 m
  blur, now 3 m): conifer slopes, tree patches on the hillsides and the brush belt along
  the creek. Woody cover is green in infrared and rough in texture, which keeps
  smooth bright fields pale. Noise still frays the margins.
- **Roads:** OpenStreetMap, plus USGS National Map and Census TIGER stretches it
  lacks, scored as ochre grooves with a lip so they cannot be mistaken for water.
- **Water:** a separate `Water` object and material at the source water level, with
  `water-mask.png` and `water-flow.png` exported for shaders.
- The DEM is smoothed (gaussian, 12 m) before any exaggeration, which removes
  its tile seams and terrace edges.
- Land height is the DEM's height above its nearest channel, so ridges, slopes
  and valleys sit where the source has them. Each channel keeps its source level.

## Authored departures (recorded in `manifest.json`)

- Model scale 1:1250 with vertical gain 2.0; source relief under ~120 m gets a further 1.2, except beside channels.
- River drawn about 12 m wide and tributaries 5–10 m.
- Pressed knobs and lumps on DEM slopes.
- Faint swells (under about a centimetre) on level wild ground. The earlier large
  invented mounds were removed because they contradicted the imagery.

## Self-assessed gaps

- The faint two-track trails visible across the fans are in no road dataset and are absent.
- Two upper gullies (north-east) end on open ground: the DEM gives only a straight line from there to the river.
- The southern tributary wanders through a hay field; its snapped course is doubtful.
- The southern conifer slope renders pale grey from overhead although its crust exists in the data.
- Field detection misses the pale mown fields in the centre and one tan field at the west edge; parcel outlines are blobby.
- Nodules and clay detail remain below the reference (see the specimen notes).
- Not yet a portable package: no GLB/atlas export, LOD or browser preview from this surface.
