"""Implicit quadtree terrain bake; implicit y increases towards north."""
import json
from pathlib import Path
import struct
import numpy as np
from scipy.ndimage import map_coordinates

from bake.tile import terrain_mesh, terrain_normals, write_glb
from bake.material import sample_fields, write_mask, detail_textures, encode_ktx
from bake.water import water_mesh, lower_water_bed


def bake_pyramid(heights, size, base_height, output, levels=5, max_error=7.5, fields=None, water=None):
    output = Path(output)
    segments = heights.shape[0]-1
    divisions = 2**(levels-1)
    if (heights.shape[0] != heights.shape[1] or levels < 1 or levels > 8
            or segments % divisions):
        raise ValueError('square grid segments must be divisible by the leaf count')
    output.mkdir(parents=True, exist_ok=True)
    half = size/2
    total_triangles = 0
    skirt = max_error*divisions*2
    low = float(heights.min())-base_height-skirt
    if fields is not None:
        for name, pixels in detail_textures().items():
            encode_ktx(pixels, output/f'detail/{name}.ktx2')
    for level in range(levels):
        count = 2**level
        cells = segments//count
        stride = 2**(levels-1-level)
        error = max_error*stride
        for x in range(count):
            for y in range(count):
                row = (count-1-y)*cells
                patch = heights[row:row+cells+1:stride, x*cells:(x+1)*cells+1:stride]
                bounds = (-half+x*size/count, -half+y*size/count,
                          -half+(x+1)*size/count, -half+(y+1)*size/count)
                if water is not None:
                    patch = lower_water_bed(patch, bounds, size, base_height, error, water)
                pos, faces = terrain_mesh(patch, bounds, base_height, error, skirt)
                low = min(low, float(pos[:,1].min()))
                path = output/f'tiles/{level}/{x}/{y}.glb'
                path.parent.mkdir(parents=True, exist_ok=True)
                colors = uv = None
                if fields is not None:
                    colors = np.repeat(sample_fields(fields, pos, size)[:, 3:4], 3, axis=1)
                    colors[:, 1:] = 0
                    if water is not None:
                        row = (.5+pos[:,2]/size)*(water['band'].shape[0]-1)
                        col = (.5+pos[:,0]/size)*(water['band'].shape[1]-1)
                        colors[:,1] = map_coordinates(water['band'], [row,col], order=1, mode='nearest')
                    uv = np.column_stack([(pos[:, 0]-bounds[0])/(bounds[2]-bounds[0]),
                                           (pos[:, 2]+bounds[3])/(bounds[3]-bounds[1])])
                    write_mask(fields, bounds, size, output/f'masks/{level}/{x}/{y}.ktx2',
                                shore_distance=water['shore_distance'] if water is not None else None)
                water_data = None
                if water is not None:
                    water_data = water_mesh(water['polygons'], water['surface'],
                                            bounds, size)
                write_glb(pos, faces, path, colors=colors, texcoords=uv, water=water_data,
                           normals=terrain_normals(patch, bounds, pos))
                total_triangles += len(faces)
        print(f'  LOD {level}: {count*count} tiles, {error:g} m TIN error', flush=True)
    high = float(heights.max())-base_height
    root = {
        'boundingVolume': {'box': [0, 0, (low+high)/2, half, 0, 0, 0, half, 0,
                                    0, 0, max((high-low)/2, .01)]},
        'geometricError': max_error*divisions*2, 'refine': 'REPLACE',
        'content': {'uri': 'tiles/{level}/{x}/{y}.glb'},
        'implicitTiling': {'subdivisionScheme': 'QUADTREE', 'subtreeLevels': levels,
                           'availableLevels': levels,
                           'subtrees': {'uri': 'subtrees/{level}/{x}/{y}.subtree'}},
    }
    tileset = {'asset': {'version': '1.1'}, 'geometricError': size, 'root': root}
    (output/'tileset.json').write_text(json.dumps(tileset, indent=2)+'\n')
    # One complete subtree. Binary header and JSON chunk are 8-byte aligned.
    availability = {'tileAvailability': {'constant': 1},
                    'contentAvailability': [{'constant': 1}],
                    'childSubtreeAvailability': {'constant': 0}}
    metadata = json.dumps(availability, separators=(',', ':')).encode()
    metadata += b' ' * (-len(metadata) % 8)
    path = output/'subtrees/0/0/0.subtree'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack('<4sIQQ', b'subt', 1, len(metadata), 0)+metadata)
    return {'tiles': (4**levels-1)//3, 'triangles': total_triangles, 'levels': levels,
            'max_error_m': max_error, 'height_range_m': [low, high]}
