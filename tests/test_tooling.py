import hashlib
from pathlib import Path

import pytest

from bake import tooling


def test_unverified_download_cannot_replace_an_existing_file(tmp_path):
    source=tmp_path/'source';source.write_bytes(b'new payload')
    target=tmp_path/'verified';target.write_bytes(b'working payload')
    with pytest.raises(ValueError,match='Checksum mismatch'):
        tooling.download_verified(source.as_uri(),target,'0'*64)
    assert target.read_bytes()==b'working payload'
    assert {p.name for p in tmp_path.iterdir()}=={'source','verified'}
    tooling.download_verified(source.as_uri(),target,hashlib.sha256(source.read_bytes()).hexdigest())
    assert target.read_bytes()==b'new payload'


def test_pinned_local_ktx_wins_over_path_and_wrong_versions_fail_early(tmp_path,monkeypatch):
    monkeypatch.setattr(tooling,'ROOT',tmp_path)
    local=tmp_path/'data/tools/ktx/bin/toktx';local.parent.mkdir(parents=True)
    local.write_text('#!/bin/sh\necho "toktx v4.4.2"\n');local.chmod(0o755)
    monkeypatch.setattr(tooling.shutil,'which',lambda name:'/untrusted/path/toktx')
    tooling.ktx_tool.cache_clear()
    try:
        path,version=tooling.ktx_tool()
        assert Path(path)==local and version=='4.4.2'
        local.write_text('#!/bin/sh\necho "toktx v4.3.0"\n')
        tooling.ktx_tool.cache_clear()
        with pytest.raises(RuntimeError,match='found 4.3.0'):
            tooling.preflight_tools(True,False)
    finally:
        tooling.ktx_tool.cache_clear()
