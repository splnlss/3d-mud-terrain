"""Pinned local tools and verified downloads used by the reproducible bake."""
from functools import cache
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]


def download_verified(url,destination,digest):
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent,delete=False) as output:
            temporary=Path(output.name)
            checksum=hashlib.sha256()
            with urlopen(url,timeout=90) as response:
                while chunk:=response.read(1024*1024):
                    checksum.update(chunk)
                    output.write(chunk)
        if checksum.hexdigest()!=digest:
            raise ValueError(f'Checksum mismatch: {destination.name}')
        temporary.replace(destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@cache
def ktx_tool():
    local=ROOT/'data/tools/ktx/bin/toktx'
    executable=str(local) if local.exists() else shutil.which('toktx')
    if executable is None:
        raise RuntimeError('KTX tools are missing. Run npm run setup:bake first.')
    result=subprocess.run([executable,'--version'],capture_output=True,text=True,check=True,timeout=15)
    match=re.search(r'\bv?(\d+\.\d+\.\d+)\b',result.stdout+result.stderr)
    actual=match.group(1) if match else 'unknown'
    if actual!='4.4.2':
        raise RuntimeError(f'Expected toktx 4.4.2, found {actual}: {executable}')
    return str(Path(executable).resolve()),actual


def preflight_tools(material,compress):
    versions={}
    command=[]
    if material:
        _,versions['ktx_software']=ktx_tool()
    if compress:
        node=shutil.which('node')
        if node is None:
            raise RuntimeError('Node.js is missing. Install Node 22.18+ and run npm ci.')
        actual=subprocess.run([node,'--version'],capture_output=True,text=True,check=True,timeout=15).stdout.strip()
        parts=tuple(int(value) for value in actual.lstrip('v').split('.')[:2])
        if parts<(22,18):
            raise RuntimeError(f'Node 22.18+ required; found {actual}')
        package=ROOT/'node_modules/@gltf-transform/core/package.json'
        if not package.exists():
            raise RuntimeError('Geometry tools are missing. Run npm ci before baking.')
        versions.update(node=actual,gltf_transform=json.loads(package.read_text())['version'])
        command=[node,str(ROOT/'scripts/compress.mjs')]
    return versions,command
