"""Portable GLB exports carry real materials/tangents, independent of a viewer."""
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


def test_atlas_is_composited_and_height_metric_is_physical():
    from bake.style.atlas import compose_atlas
    maps=compose_atlas((0,0,500,500),128,{'seed':4271},np.full((9,9),.65))
    assert maps['base_color'].shape==(128,128,3)
    assert maps['normal'].shape==(128,128,3)
    assert np.ptp(maps['height'])>0
    np.testing.assert_allclose(np.linalg.norm(maps['normal'],axis=-1),1,atol=1e-5)
    assert maps['uv_surface_metric']['metres_per_uv']==[500,500]


def test_glb_validator_rejects_missing_tangents_and_escaping_map(tmp_path):
    # A source-package check must fail usefully, before engine import.
    manifest={'schema_version':1,'units':'m','axes':'x-east,y-up,z-south',
              'files':['../escape.glb'],'lods':[]}
    (tmp_path/'manifest.json').write_text(json.dumps(manifest))
    run=subprocess.run(['node','scripts/validate-style-package.mjs',str(tmp_path)],capture_output=True,text=True)
    assert run.returncode!=0
    assert 'escape' in run.stderr.lower() or 'relative' in run.stderr.lower()


def test_validator_rejects_normal_mapped_glb_without_tangents(tmp_path):
    import base64,io,struct
    from PIL import Image
    from bake.tile import write_glb
    from tests.test_tile import unpack_glb
    positions=np.array([[0,0,0],[1,0,0],[0,0,1]],dtype='float32')
    path=tmp_path/'mesh.glb'
    write_glb(positions,[[0,2,1]],path,normals=np.tile([0,1,0],(3,1)),texcoords=np.array([[0,0],[1,0],[0,1]]))
    doc,binary=unpack_glb(path)
    stream=io.BytesIO();Image.new('RGB',(2,2),(128,128,255)).save(stream,format='PNG')
    doc['images']=[{'uri':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()}]
    doc['textures']=[{'source':0}];doc['materials'][0]['normalTexture']={'index':0}
    chunk=json.dumps(doc).encode();chunk+=b' '*(-len(chunk)%4)
    binary+=b'\0'*(-len(binary)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(chunk)+len(binary))+struct.pack('<I4s',len(chunk),b'JSON')+chunk+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
    (tmp_path/'manifest.json').write_text(json.dumps({'schema_version':1,'files':['mesh.glb'],
       'lods':[{'path':'mesh.glb','bounds_m':[[0,0,0],[1,0,1]]}]}))
    run=subprocess.run(['node','scripts/validate-style-package.mjs',str(tmp_path)],capture_output=True,text=True)
    assert run.returncode!=0
    assert 'TANGENT' in run.stderr


def test_validator_measures_world_bounds_after_node_transforms(tmp_path):
    import struct
    from bake.tile import write_glb
    from tests.test_tile import unpack_glb
    path=tmp_path/'mesh.glb';write_glb([[0,0,0],[1,0,0],[0,0,1]],[[0,2,1]],path)
    doc,binary=unpack_glb(path);doc['nodes'][0]['translation']=[100,20,-40]
    chunk=json.dumps(doc).encode();chunk+=b' '*(-len(chunk)%4);binary+=b'\0'*(-len(binary)%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(chunk)+len(binary))+struct.pack('<I4s',len(chunk),b'JSON')+chunk+struct.pack('<I4s',len(binary),b'BIN\0')+binary)
    (tmp_path/'manifest.json').write_text(json.dumps({'schema_version':1,'files':['mesh.glb'],
       'lods':[{'path':'mesh.glb','bounds_m':[[100,20,-40],[101,20,-39]]}]}))
    run=subprocess.run(['node','scripts/validate-style-package.mjs',str(tmp_path)],capture_output=True,text=True)
    assert run.returncode==0,run.stderr
