# Granular material study

`granular-study-v1.png` was generated using the built-in image-generation tool as
an attempted scalar sculpting stamp. Inspection showed photographic/baked lighting,
so it is retained **only as a shape/material study**, not used as albedo, calibrated
height, displacement or normal-map data. Its irregular fractured plate-like clods
help guide the editable geometry. Real maps are derived from authored geometry.

Prompt: Create a square grayscale material height stamp for an aged handmade clay
relief, dense uneven angular knobbly aggregates and fused crusts, deep gaps, pits,
fractured flakes, mixed sizes and bare spaces; avoid Voronoi cells, regular pebbles,
round berries, fabric noise, smooth domes and rows. Encode elevation only, white
raised tops/gray flanks/black cavities; no illumination, shadows, perspective, colour,
text or frames; compatible edges for tiling. The generated result did not satisfy
the no-lighting requirement and was not promoted to material data.

## Clay colour draft v2

`clay-albedo-v2.png` is an AI-generated material interpretation guided by
`../style-studies/04-canyon.png`. Prompt requested seamless, orthographic,
neutral-lit base colour: warm grey-brown fused granular clay, ochre rubbed
flakes and dusty flecks; no landscape, regular cells or isolated rocks.
Generated using the built-in image tool on 2026-11-12. It retains visible
micro shadows and is therefore a **colour draft with residual shading**, not
a calibrated, fully de-lit scan. It must not be converted to height or normals.

`bake/style/granular.py` authors independent periodic physical relief and
finish maps. The matching source preview uses shared world-space box projection
for colour and finish, and physical bump relief. Their fine features are not
point-for-point registered to the generated colour. This is a fidelity probe;
a final coherent scan or geometry-baked colour/normal set remains desirable.
