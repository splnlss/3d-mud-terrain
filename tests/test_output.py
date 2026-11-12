"""A failed bake must not replace the working scene or leave stale assets."""
import json
from pathlib import Path

import pytest

from bake.output import output_stage


def complete(path, value):
    (path/'tileset.json').write_text(json.dumps({'value': value}))
    (path/'manifest.json').write_text(json.dumps({'value': value}))
    (path/'terrain.glb').write_bytes(value.encode())


def test_failed_bake_keeps_the_previous_scene(tmp_path):
    dest = tmp_path/'terrain'
    dest.mkdir()
    complete(dest, 'old')
    with pytest.raises(RuntimeError, match='encoder failed'):
        with output_stage(dest) as stage:
            complete(stage, 'new')
            raise RuntimeError('encoder failed')
    assert (dest/'terrain.glb').read_bytes() == b'old'
    assert sorted(p.name for p in tmp_path.iterdir()) == ['terrain']


def test_successful_bake_replaces_old_generated_assets_as_one_scene(tmp_path):
    dest = tmp_path/'terrain'
    dest.mkdir()
    complete(dest, 'old')
    (dest/'masks').mkdir()
    (dest/'masks/stale.ktx2').write_bytes(b'old')
    with output_stage(dest) as stage:
        complete(stage, 'new')
        assert (dest/'terrain.glb').read_bytes() == b'old'
    assert (dest/'terrain.glb').read_bytes() == b'new'
    assert not (dest/'masks').exists()


def test_output_folder_with_unrelated_files_is_never_replaced(tmp_path):
    dest = tmp_path/'terrain'
    dest.mkdir()
    (dest/'important.txt').write_text('keep')
    with pytest.raises(ValueError, match='unrecognised'):
        with output_stage(dest) as stage:
            complete(stage, 'new')
    assert (dest/'important.txt').read_text() == 'keep'
