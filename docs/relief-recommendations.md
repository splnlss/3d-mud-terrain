# Relief tiles: open recommendations (noted 2026-11-13)

Status notes, not accepted work. Each item says what was observed and what to do about it.
Process and commands: [relief process](relief-process.md). Evidence: `docs/reviews/relief-tiles/`.

## Walking view (within a few metres of the ground)

1. **Ground-level view at San Luis looks bad (undiagnosed).** A capture at about 40 m showed a blurry, stretched
   texture with heavy dark blotches and no fine dirt detail. First check whether the finest tiles had finished
   loading; then check tree and brush lumps, which appear to shade far too darkly from close range.
2. **Dirt detail repeats and reads as ripples** from about 30 m. Give clods more irregular shapes and add a second,
   larger pattern so the 6.9 m repeat is not visible.
3. **Dirt detail is the same everywhere.** It covers fields, roads, forest and water alike. Vary it by ground type
   (bare soil, field rows, road bed, forest floor, wet channel) using the masks each tile already carries.
4. **Tree and brush lumps are spiky up close.** They read as small sharp facets, not pressed clay. Make the finest
   lump sizes rounder and broader; the two finest sizes were already reduced once.
5. **Camera height comes from a 10 m ground map** built from the finest mesh. Under trees the camera can end up
   inside lumps. Either add collision against the loaded mesh or raise eye height where cover is high.
6. **Level 7 only covers 5 km around San Luis.** Beyond that the finest ground is level 6 (about 1.15 m per texel).
   Baking finer levels over wide areas is not feasible; the shared detail material has to carry the close range.

## Terrain and seams

7. **A thin dark seam shows where a coarse tile meets a finer one** (seen once in the middle-distance ridge view).
   Far smaller than the old walls, but present. Match edge vertices between levels or blend across the border.
8. **Texture detail still changes when a tile refines**, because each level's clay shading is authored separately.
   The mesh no longer changes. Cross-fade textures, or author shading from one shared multi-scale field.
9. **Valley floor is flatter at ×1.25** than at ×2. This was the user's choice; revisit only if the floor reads empty.

## Rivers, creeks and roads

10. **Rivers look too wide from far away.** Each stream is drawn at a minimum readable width per level, which turns
    mountain creeks into broad pale ribbons at overview. Reduce the minimum, or fade minor streams by level.
11. **Creek accuracy is not in the tile baker.** The single-tile pipeline snaps tributaries to the tree line, derives
    gullies from the DEM and uses Google 3D Tiles terrain; the regional tiles use NHD lines only, so creeks missing
    from NHD are missing. Port those steps.
12. **Faint two-track trails are absent.** They are in none of the road datasets; they would have to be traced from imagery.
13. **Roads are hard to pick out in mountain views**, though the user found them fine from the wide overview.

## Fields, buildings and tone

14. **Field detection is tuned on one scene.** It missed pale mown fields and one tan field on the Culebra tile and
    produces blobby outlines. Straighten outlines and retune on valley-floor tiles.
15. **Centre pivots are found once for the region** (1,572 circles, by outline). Not yet checked for false circles.
16. **Homes come only from OpenStreetMap** (11,480 buildings). Rural homes not mapped there are missing.
17. **New Mexico imagery is tone-matched to Colorado along 37° N** with one gain and offset per band. Check the
    state line at close range.
18. **Snow line is a fixed elevation band** (3,650–4,050 m) with noise. It ignores aspect.

## Delivery and performance

19. **Geometry is uncompressed float positions.** Add mesh compression (meshopt) once the look is settled.
20. **The shader inputs (water mask, flow direction) are exported but unused.** No engine shader consumes them yet.
21. **The preview has no shadows**, so relief reads flatter than the Blender renders. Add a shadow pass or baked occlusion.
22. **Google 3D Tiles view has small seams when zoomed close** (single-precision positions at Earth scale).
23. **The official 3D Tiles validator would not run under this Node version.** Tile GLBs pass the glTF validator apart
    from its not recognising KTX2 images. Run the tileset validator on a supported Node.
24. **Bake memory.** Each tile peaks near 3.5 GB; five workers is the limit on this machine. A code change that
    touches tile authoring should be measured on one tile (`/usr/bin/time -l`) before a parallel bake; an
    unmeasured change exhausted memory and the machine restarted on 2026-11-13.
25. **Nothing is committed.** All of this work is uncommitted in the worktree.
