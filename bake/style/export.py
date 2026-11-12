"""Prepare unique-UV material atlases and run the independent Blender exporter."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from PIL import Image
from bake.style.atlas import compose_atlas
from bake.style.package import write_package,package_stage

ROOT=Path(__file__).resolve().parents[2]


def prepare_atlases(package,resolution=2048):
    package=Path(package);manifest=json.loads((package/'manifest.json').read_text())
    fields=np.load(package/'source/sculpted.npz');size=manifest['size_m'];count=4;span=size/count
    n=fields['height'].shape[0]-1;cells=[]
    for row in range(count):
        for col in range(count):
            row0=row*n//count;row1=(row+1)*n//count;col0=col*n//count;col1=(col+1)*n//count
            bounds=[-size/2+col*span,size/2-(row+1)*span,-size/2+(col+1)*span,size/2-row*span]
            crust=fields['crust'][row0:row1+1,col0:col1+1]
            atlas=compose_atlas(bounds,resolution,manifest['recipe'],crust)
            name=f'{row}-{col}';paths={}
            for key in ['base_color','normal']:
                values=atlas[key]
                if key=='normal':values=values*.5+.5
                path=f'textures/cell-{name}-{key}.png'
                Image.fromarray(np.uint8(np.clip(values,0,1)*255)).save(package/path)
                paths[key]=path
            orm=np.stack([atlas['ao'],atlas['roughness'],np.zeros_like(atlas['ao'])],axis=-1)
            path=f'textures/cell-{name}-orm.png';Image.fromarray(np.uint8(orm*255)).save(package/path);paths['orm']=path
            height=atlas['height'];minimum=float(height.min());extent=float(np.ptp(height))
            path=f'height/cell-{name}.png';Image.fromarray(np.uint16((height-minimum)/extent*65535)).save(package/path);paths['height']=path
            # Raw float data offers an engine-neutral precision baseline for POM.
            path=f'height/cell-{name}.f32';height.astype('<f4').tofile(package/path);paths['height_float']=path
            metric=atlas['uv_surface_metric'];metric.update(uv_origin=[0,0],tangent_frame='MikkTSpace',
                normal_axis='geometric-normal',surface_jacobian='derived from position/UV derivatives; tangent-space metre metric')
            cells.append({'id':name,'bounds_xnorth_m':bounds,'source_window':[row0,row1,col0,col1],
                          'maps':paths,'texture_size':resolution,'height_min_m':minimum,'height_range_m':extent,
                          'height_zero':1.,'span_m':span,'uv_surface_metric':metric})
            print(f'Atlas {name}: {resolution}²',flush=True)
    manifest['cells']=cells;manifest['files']=sorted(str(p.relative_to(package)) for p in package.rglob('*')
        if p.is_file() and p.name not in ['manifest.json','.terrain-style-package'])
    write_package(package,manifest)


def export_package(package,resolution=2048):
    package=Path(package)
    blender=shutil.which('blender')
    if not blender:raise ValueError('Blender CLI is required for portable export')
    with package_stage(package) as stage:
        shutil.copytree(package,stage,dirs_exist_ok=True)
        prepare_atlases(stage,resolution)
        subprocess.run([blender,'--background','--python-exit-code','1','--python',str(ROOT/'bake/style/blender_bake.py'),
                        '--','--package',str(stage.resolve()),'--action','bake'],check=True,cwd=ROOT)
        manifest=json.loads((stage/'manifest.json').read_text())
        manifest['files']=sorted(str(p.relative_to(stage)) for p in stage.rglob('*')
            if p.is_file() and p.name not in ['manifest.json','.terrain-style-package'])
        write_package(stage,manifest)
        if len(manifest.get('lods',[]))!=16:raise ValueError('incomplete patch mesh export')
        subprocess.run(['node',str(ROOT/'scripts/validate-style-package.mjs'),str(stage.resolve())],check=True,cwd=ROOT)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package',default='data/style-patch');parser.add_argument('--resolution',type=int,default=2048)
    args=parser.parse_args();export_package(args.package,args.resolution)
