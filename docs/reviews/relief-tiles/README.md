# Regional relief tileset (2026-11-13)

**Not visually accepted.** Browser captures of `data/relief-tiles/tileset.json`
through the preview page `/relief.html` (PlayCanvas, real-time light, no shadows).

| View | Shows |
|---|---|
| [Region](region-overview.jpg) | Whole 112.64 km square from the root and level-1 tiles. |
| [Alamosa, Rio Grande, pivots](alamosa-pivots-rio-grande.jpg) | Level-3 tiles: river meanders, town street grid, combed centre pivots. A lower-detail tile shows a skirt wall where it meets its neighbour. |
| [Culebra foothills](culebra-foothills.jpg) | Level-3 tiles close up: detail is coarse at this distance until finer levels are baked. |
| [Alamosa at level 4](alamosa-level4.jpg) | Level-4 tiles: Rio Grande meanders, street grid, riparian crust. |
| [Culebra Creek, levels 5–6](culebra-creek-levels5-6.jpg) | Finest baked tiles, captured with `?cacheMB=4000`. Hills read as steep cones here. |

357 tiles: levels 0–4 cover the whole region; levels 5–6 exist only around Culebra Creek (8 tiles each).
With the default 900 MB cache the preview holds about 15 tiles and cannot refine past level 4 in a close view.

Process, rules and limits: [relief process](../../relief-process.md#regional-tileset-3d-tiles).
