"""Repeatable visual iteration from the untouched DEM, with staged publication."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np
from scipy.ndimage import map_coordinates
from bake.style.surface import sculpt_field
from bake.style.shore import integrate_shore
from bake.style.package import package_stage,write_package

ROOT=Path(__file__).resolve().parents[2]


def refine(package,recipe_path,render=False,views='close'):
    package=Path(package);recipe=json.loads(Path(recipe_path).read_text())
    blender=shutil.which('blender')
    if render and not blender:raise ValueError('Blender is required for source renders')
    with package_stage(package) as stage:
        shutil.copytree(package,stage,dirs_exist_ok=True)
        manifest=json.loads((stage/'manifest.json').read_text());source=np.load(stage/'source/dem.npy')
        recipe['base_elevation_m']=manifest['base_elevation_m']
        count=round(manifest['size_m']/recipe['author_spacing_m'])+1
        ix=np.linspace(0,source.shape[1]-1,count);iy=np.linspace(0,source.shape[0]-1,count)
        rows,cols=np.meshgrid(iy,ix,indexing='ij');upsampled=map_coordinates(source,[rows,cols],order=3)
        half=manifest['size_m']/2
        east,north=np.meshgrid(np.linspace(-half,half,count),np.linspace(half,-half,count))
        fields=sculpt_field(east,north,upsampled,recipe)
        np.savez_compressed(stage/'source/sculpted.npz',**{k:v for k,v in fields.items() if isinstance(v,np.ndarray)})
        (stage/'source/clasts.json').write_text(json.dumps(fields['clast_instances']))
        (stage/'source/recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
        manifest.update(recipe=recipe,feature_scale_m=recipe['feature_scale_m'],
                        exports_status='stale after source refinement; run bake.style.export before using delivery meshes',
                        artistic_departures=[{'kind':'sculpted-clay','recipe':'source/recipe.json'}])
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        integrate_shore(stage)
        manifest=json.loads((stage/'manifest.json').read_text())
        manifest['cameras']['close'].update(target=[0,190,300],distance=850,pitch_deg=26,yaw_deg=80)
        manifest['review_render_settings']={'key_position':[-800,-500,600],'key_energy':2.4,
           'key_angle_radians':.065,'environment_strength':.18,'tone_mapping':'AgX',
           'exposure_stops':1,'renderer':'Cycles','samples':32,'denoising':True,
           'note':'source material authoring view; portable export must be rebuilt and independently reviewed'}
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        if render:
            subprocess.run([blender,'--background','--python-exit-code','1','--python',
                str(ROOT/'bake/style/blender_preview.py'),'--','--package',str(stage.resolve()),'--views',views],check=True)
        manifest['files']=sorted(str(p.relative_to(stage)) for p in stage.rglob('*')
            if p.is_file() and p.name not in ['manifest.json','.terrain-style-package'])
        write_package(stage,manifest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',default='data/style-patch')
    p.add_argument('--recipe',default='configs/style-materials.json');p.add_argument('--render',action='store_true')
    p.add_argument('--views',default='close');args=p.parse_args();refine(args.package,args.recipe,args.render,args.views)
