"""Adaptive terrain mesh and static tile writer. All distances are metres."""
import json
from pathlib import Path
import struct

import numpy as np
from pydelatin import Delatin
from scipy.ndimage import map_coordinates


def write_glb(positions, triangles, path, colors=None, texcoords=None, normals=None, water=None):
    """Write a minimal glTF 2.0 mesh, with no dependency on a scene exporter."""
    positions = np.asarray(positions, dtype='<f4')
    triangles = np.asarray(triangles, dtype='<u4')
    vertex_bytes, index_bytes = positions.tobytes(), triangles.tobytes()
    binary = vertex_bytes + index_bytes
    doc = {
        'asset': {'version': '2.0', 'generator': 'san-luis-relief'},
        'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1,
                                   'material': 0}]}],
        'materials': [{'name': 'terrain', 'pbrMetallicRoughness': {
            'baseColorFactor': [0.55, 0.43, 0.29, 1], 'metallicFactor': 0,
            'roughnessFactor': 1}}],
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [
            {'buffer': 0, 'byteOffset': 0, 'byteLength': len(vertex_bytes), 'target': 34962},
            {'buffer': 0, 'byteOffset': len(vertex_bytes), 'byteLength': len(index_bytes),
             'target': 34963}],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': len(positions),
             'type': 'VEC3', 'min': positions.min(axis=0).tolist(),
             'max': positions.max(axis=0).tolist()},
            {'bufferView': 1, 'componentType': 5125, 'count': triangles.size,
             'type': 'SCALAR'}],
    }
    for semantic, values, kind in [('COLOR_0', colors, 'VEC3'),
                                    ('TEXCOORD_0', texcoords, 'VEC2'),
                                    ('NORMAL', normals, 'VEC3')]:
        if values is None:
            continue
        values = np.asarray(values, dtype='<f4')
        view = len(doc['bufferViews'])
        accessor = len(doc['accessors'])
        doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary),
                                   'byteLength': values.nbytes, 'target': 34962})
        doc['accessors'].append({'bufferView': view, 'componentType': 5126,
                                'count': len(values), 'type': kind})
        doc['meshes'][0]['primitives'][0]['attributes'][semantic] = accessor
        binary += values.tobytes()
    if water is not None and len(water[0]):
        water_positions, water_faces = water
        attributes = {}
        index_accessor = None
        for semantic, values, kind in [('POSITION', water_positions, 'VEC3'),
                                        ('indices', water_faces.ravel(), 'SCALAR')]:
            values = np.asarray(values, dtype='<u4' if semantic=='indices' else '<f4')
            view = len(doc['bufferViews'])
            accessor = len(doc['accessors'])
            doc['bufferViews'].append({'buffer': 0, 'byteOffset': len(binary),
                                       'byteLength': values.nbytes,
                                       'target': 34963 if semantic=='indices' else 34962})
            definition = {'bufferView': view, 'componentType': 5125 if semantic=='indices' else 5126,
                          'count': len(values), 'type': kind}
            if semantic == 'POSITION':
                definition.update({'min': values.min(axis=0).tolist(), 'max': values.max(axis=0).tolist()})
            doc['accessors'].append(definition)
            if semantic=='indices':
                index_accessor = accessor
            else:
                attributes[semantic] = accessor
            binary += values.tobytes()
        doc['materials'].append({'name': 'painted-water', 'pbrMetallicRoughness': {
            'baseColorFactor': [.79,.78,.77,1], 'metallicFactor': 0, 'roughnessFactor': 1}})
        doc['meshes'][0]['primitives'].append({'attributes': attributes, 'indices': index_accessor,
                                              'material': 1})
    doc['buffers'][0]['byteLength'] = len(binary)
    metadata = json.dumps(doc, separators=(',', ':')).encode()
    metadata += b' ' * (-len(metadata) % 4)
    binary += b'\x00' * (-len(binary) % 4)
    length = 12 + 8 + len(metadata) + 8 + len(binary)
    Path(path).write_bytes(struct.pack('<4sII', b'glTF', 2, length)
                           + struct.pack('<I4s', len(metadata), b'JSON') + metadata
                           + struct.pack('<I4s', len(binary), b'BIN\x00') + binary)


def terrain_mesh(heights, bounds, base_height, max_error=1.0, skirt_depth=0):
    """Mesh a north-first DEM; bounds are sample-centre (west,south,east,north)."""
    heights = np.asarray(heights, dtype='float32')
    if (heights.ndim != 2 or min(heights.shape) < 2 or not np.isfinite(heights).all()
            or heights.min() < -500 or heights.max() > 20000):
        raise ValueError('invalid or missing elevation samples')
    if max_error <= 0:
        raise ValueError('max_error must be positive')
    west, south, east, north = bounds
    if east <= west or north <= south:
        raise ValueError('bounds must have positive area')
    # Delatin's y is north-up, despite its input array being north-first.
    tin = Delatin(heights, max_error=max_error)
    vertices = tin.vertices
    positions = np.column_stack([
        west + vertices[:, 0] / (heights.shape[1]-1) * (east-west),
        vertices[:, 2] - base_height,
        -(south + vertices[:, 1] / (heights.shape[0]-1) * (north-south)),
    ]).astype('float32')
    triangles = tin.triangles.copy()
    if skirt_depth > 0:
        strips, faces = [], []
        offset = len(positions)
        for axis, value, order_axis in [(0, west, 2), (0, east, 2),
                                         (2, -north, 0), (2, -south, 0)]:
            ids = np.where(np.isclose(positions[:, axis], value, rtol=0, atol=.01))[0]
            ids = ids[np.argsort(positions[ids, order_axis])]
            bottom = positions[ids].copy()
            bottom[:, 1] -= skirt_depth
            strips.append(bottom)
            for i in range(len(ids)-1):
                # Each skirt is double-sided geometrically, avoiding extra materials.
                a, b, c, d = int(ids[i]), int(ids[i+1]), offset+i, offset+i+1
                faces.extend([[a, b, c], [b, d, c], [b, a, c], [d, b, c]])
            offset += len(ids)
        positions = np.vstack([positions, *strips])
        triangles = np.vstack([triangles, faces]).astype('uint32')
    return positions, triangles


def bake_tile(heights, bounds, base_height, output, max_error=1.0):
    positions, triangles = terrain_mesh(heights, bounds, base_height, max_error)
    west, south, east, north = bounds
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    write_glb(positions, triangles, output/'terrain.glb', normals=terrain_normals(heights, bounds, positions))
    low, high = float(positions[:, 1].min()), float(positions[:, 1].max())
    box = [(west+east)/2, (south+north)/2, (low+high)/2,
           (east-west)/2, 0, 0, 0, (north-south)/2, 0, 0, 0, max((high-low)/2, .01)]
    tileset = {'asset': {'version': '1.1'}, 'geometricError': max(east-west, north-south),
               'root': {'boundingVolume': {'box': box}, 'geometricError': 0,
                        'refine': 'REPLACE', 'content': {'uri': 'terrain.glb'}}}
    (output/'tileset.json').write_text(json.dumps(tileset, indent=2)+'\n')
    return {'vertices': len(positions), 'triangles': len(triangles),
            'max_error_m': max_error, 'height_range_m': [low, high]}


def terrain_normals(heights, bounds, positions):
    west, south, east, north = bounds
    dy, dx = np.gradient(heights, (north-south)/(heights.shape[0]-1),
                         (east-west)/(heights.shape[1]-1))
    col = (positions[:,0]-west)/(east-west)*(heights.shape[1]-1)
    row = (positions[:,2]+north)/(north-south)*(heights.shape[0]-1)
    slope_x = map_coordinates(dx, [row,col], order=1, mode='nearest')
    slope_z = map_coordinates(dy, [row,col], order=1, mode='nearest')
    normals = np.column_stack([-slope_x, np.ones_like(slope_x), -slope_z])
    normals /= np.linalg.norm(normals, axis=1, keepdims=True)
    return normals.astype('float32')
