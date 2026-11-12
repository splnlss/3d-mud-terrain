"""Catch invalid terrain geometry, bounds and glTF/3D Tiles axis conversion."""
import json
import struct

import numpy as np
import pytest

from bake.tile import bake_tile


def unpack_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', raw)
    assert (magic, version, length) == (b'glTF', 2, len(raw))
    json_length, kind = struct.unpack_from('<I4s', raw, 12)
    assert kind == b'JSON'
    doc = json.loads(raw[20:20 + json_length])
    offset = 20 + json_length
    bin_length, kind = struct.unpack_from('<I4s', raw, offset)
    assert kind == b'BIN\x00'
    return doc, raw[offset + 8:offset + 8 + bin_length]


def attribute(doc, binary, accessor_index):
    accessor = doc['accessors'][accessor_index]
    view = doc['bufferViews'][accessor['bufferView']]
    dtype = {5126: '<f4', 5125: '<u4'}[accessor['componentType']]
    width = {'VEC3': 3, 'SCALAR': 1}[accessor['type']]
    return np.frombuffer(binary, dtype=dtype, count=accessor['count'] * width,
                         offset=view.get('byteOffset', 0)).reshape(-1, width)


def test_bake_preserves_real_relief_orientation_and_encloses_every_vertex(tmp_path):
    # North row is higher; east column is higher. Metres, not arbitrary noise.
    heights = np.array([[110, 120, 130], [100, 110, 120], [90, 100, 110]], dtype='float32')
    bake_tile(heights, (100, 200, 120, 220), 90, tmp_path, max_error=0.1)
    tileset = json.loads((tmp_path/'tileset.json').read_text())
    doc, binary = unpack_glb(tmp_path/tileset['root']['content']['uri'])
    primitive = doc['meshes'][0]['primitives'][0]
    positions = attribute(doc, binary, primitive['attributes']['POSITION'])
    normals = attribute(doc, binary, primitive['attributes']['NORMAL'])
    np.testing.assert_allclose(np.linalg.norm(normals, axis=1), 1, atol=1e-5)
    np.testing.assert_allclose(normals, np.tile([-1,1,1], (len(normals),1))/np.sqrt(3), atol=1e-5)
    # glTF x=east, y=elevation, z=south; tiles use x=east,y=north,z=elevation.
    assert any(np.allclose(p, [100, 20, -220]) for p in positions)
    assert any(np.allclose(p, [120, 40, -220]) for p in positions)
    indices = attribute(doc, binary, primitive['indices']).ravel()
    assert indices.max() < len(positions)
    triangles = positions[indices].reshape(-1, 3, 3)
    normals = np.cross(triangles[:, 1]-triangles[:, 0], triangles[:, 2]-triangles[:, 0])
    assert (normals[:, 1] > 0).all(), 'terrain faces must point upward'
    box = tileset['root']['boundingVolume']['box']
    world = positions[:, [0, 2, 1]] * [1, -1, 1]
    center, half = np.array(box[:3]), np.array([box[3], box[7], box[11]])
    assert (np.abs(world-center) <= half+1e-4).all()
    assert tileset['asset']['version'] == '1.1'


@pytest.mark.parametrize('heights', [np.array([[1., np.nan], [2., 3.]]),
                                     np.array([[1., -999999], [2., 3.]])])
def test_missing_dem_samples_cannot_silently_turn_into_spikes(heights, tmp_path):
    with pytest.raises(ValueError, match='elevation'):
        bake_tile(heights, (0, 0, 10, 10), 0, tmp_path)


def test_same_input_regenerates_identical_static_assets(tmp_path):
    heights = np.arange(25, dtype='float32').reshape(5, 5) + 2300
    for name in ['a', 'b']:
        bake_tile(heights, (-20, -20, 20, 20), 2300, tmp_path/name)
    for name in ['terrain.glb', 'tileset.json']:
        assert (tmp_path/'a'/name).read_bytes() == (tmp_path/'b'/name).read_bytes()
