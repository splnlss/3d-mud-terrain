"""Small matched mesh/material LOD fixtures with protected boundary samples."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import Delaunay
from scipy.interpolate import LinearNDInterpolator
from PIL import Image
from bake.style.maps import normal_from_height
from bake.tile import write_glb


def residual_normal(master,receiver,spacing_m):
    return normal_from_height(master-receiver,spacing_m)


def derive_lods(master_path: Path,recipe: dict,output: Path):
    source=np.load(master_path);height=source['height'];n,m=height.shape
    protected=source['protected'] if 'protected' in source else np.zeros(height.shape,bool)
    protected=protected.copy();protected[[0,-1],:]=True;protected[:,[0,-1]]=True
    west,south,east,north=recipe['bounds_m'];spacing=(east-west)/(m-1)
    xx,zz=np.meshgrid(np.linspace(west,east,m),-np.linspace(north,south,n))
    output=Path(output);output.mkdir(parents=True,exist_ok=True);levels=[]
    for level,stride in enumerate([1,2,4]):
        keep=protected.copy();keep[::stride,::stride]=True
        uv=np.c_[xx[keep],zz[keep]];triangulation=Delaunay(uv)
        receiver=LinearNDInterpolator(triangulation,height[keep])(xx,zz)
        error=float(np.max(abs(height-receiver)))
        pos=np.c_[uv[:,0],height[keep],uv[:,1]].astype('float32')
        normal=normal_from_height(height,spacing)[keep]
        # Tangent up maps to north (negative south), geometric normal maps accordingly.
        normals=np.c_[normal[:,0],normal[:,2],-normal[:,1]]
        triangles=triangulation.simplices[:,[0,2,1]]
        path=f'fixture-{level}.glb'
        write_glb(pos,triangles,output/path,normals=normals)
        receiver_path=f'receiver-{level}.npy';np.save(output/receiver_path,receiver.astype('float32'))
        residual=residual_normal(height,receiver,spacing)
        Image.fromarray(np.uint8(np.clip(residual*.5+.5,0,1)*255)).save(output/f'residual-{level}.png')
        levels.append({'level':level,'path':path,'receiver':receiver_path,'geometric_error_m':error,
                       'residual_normal':f'residual-{level}.png','texture_dimensions':[m,n],
                       'bounds_m':[pos.min(axis=0).tolist(),pos.max(axis=0).tolist()],
                       'parent':None if level==2 else f'fixture-{level+1}.glb',
                       'selection':{'screen_error_px':2,'material_mode':'residual-normal' if level else 'geometric'}})
    (output/'lods.json').write_text(json.dumps(levels,indent=2)+'\n')
    return levels
