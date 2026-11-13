"""A complete quadtree must have valid availability and nested tile coordinates."""
import json
import struct

import numpy as np

from bake.pyramid import bake_pyramid
from tests.test_tile import unpack_glb, attribute


def test_quadtree_covers_north_and_south_without_axis_flip(tmp_path):
    heights = np.tile(np.linspace(140, 100, 9)[:, None], (1, 9)).astype('float32')
    bake_pyramid(heights, 80, 100, tmp_path, levels=2, max_error=1)
    doc = json.loads((tmp_path/'tileset.json').read_text())
    root = doc['root']
    assert root['implicitTiling']['subdivisionScheme'] == 'QUADTREE'
    assert root['implicitTiling']['availableLevels'] == 2
    assert root['content']['uri'] == 'tiles/{level}/{x}/{y}.glb'
    assert len(list(tmp_path.rglob('*.glb'))) == 5
    assert (tmp_path/'subtrees/0/0/0.subtree').exists()
    raw = (tmp_path/'subtrees/0/0/0.subtree').read_bytes()
    magic, version, length, binary_length = struct.unpack_from('<4sIQQ', raw)
    assert (magic, version, binary_length) == (b'subt', 1, 0)
    availability = json.loads(raw[24:24+length])
    assert availability['tileAvailability'] == {'constant': 1}
    assert availability['childSubtreeAvailability'] == {'constant': 0}
    # y=0 is SOUTH in 3D Tiles' implicit quadtree, though raster rows are north-first.
    gltf, binary = unpack_glb(tmp_path/'tiles/1/0/0.glb')
    pos = attribute(gltf, binary, gltf['meshes'][0]['primitives'][0]['attributes']['POSITION'])
    assert pos[:, 2].min() >= 0  # glTF south is positive z
    assert pos[:, 2].max() == 40
    assert pos[:, 1].max() == 20
    # Skirts must extend below the terrain without moving boundary XY coordinates.
    assert pos[:, 1].min() < 0


def test_invalid_grid_cannot_leave_slivers_uncovered(tmp_path):
    import pytest
    with pytest.raises(ValueError, match='divisible'):
        bake_pyramid(np.ones((8, 8), dtype='float32')*100, 80, 100, tmp_path, levels=3)
