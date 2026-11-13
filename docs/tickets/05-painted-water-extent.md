# 05 — Place flat painted water

## Goal

The Rio Grande, Culebra Creek, Sanchez Reservoir, and acequias appear as pale, flat model-water sheets in the browser.

## Scope

- **Bake:** combine NHD and Sentinel-2 NDWI, fill DEM depressions for per-body heights, dilate channels into legible rivulets, and create flat water polygons.
- **Tiles:** include water as a second primitive inside each relevant terrain GLB, with seam-safe shoreline geometry and bounds.
- **Viewer:** render a simple matte pale warm grey-beige water material and expose water-level tuning in the debug panel.

## Acceptance criteria

- Fixed overhead and oblique screenshots show all four named water classes in plausible positions against NHD/NDWI overlays, without flooded hills or missing major reaches.
- Water surfaces are planar, meet steep banks at a sharp line, and provide the base of **S4**; no visible tile gaps occur along a channel.
- Relevant GLBs contain terrain and water primitives, with no separate water tileset; the viewer displays newly streamed water tiles.
- Bake manifest records NHD and Sentinel-2 source/provenance and chosen dilation/depression-fill parameters.

## Blocked by

03, 04.

## Notes

Keep the initial material still and matte. The rim, grain, and subtle animation arrive in 06.

## Status

**Implemented; water geography review remains open.** The manifest records USGS NHD source URLs and hashes, Sentinel-2 acquisitions, water processing parameters, and 337 GLBs with terrain and water primitives. Water geometry tests and the 341-tile asset validator passed. [05-rio-grande-gorge.jpg](../evidence/05-rio-grande-gorge.jpg) and [06-sanchez-reservoir.jpg](../evidence/06-sanchez-reservoir.jpg) show planar pale water and a sharp contact. Some narrow reaches read as bright lines; a reach-by-reach NHD/NDWI overlay review and physical-device seam inspection remain unverified.
