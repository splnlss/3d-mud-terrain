"""Attach coherent material masters and sculpted source to an existing package."""
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image
from bake.style.surface import sculpt_field
from bake.style.maps import author_material
from bake.style.package import write_package,package_stage


def _author(package,recipe_path='configs/style-materials.json'):
    package=Path(package);manifest=json.loads((package/'manifest.json').read_text())
    recipe=json.loads(Path(recipe_path).read_text());recipe['base_elevation_m']=manifest['base_elevation_m']
    h=np.load(package/'source/dem.npy');size=manifest['size_m']
    x,north=np.meshgrid(np.linspace(-size/2,size/2,h.shape[1]),np.linspace(size/2,-size/2,h.shape[0]))
    result=sculpt_field(x,north,h,recipe)
    np.savez_compressed(package/'source/sculpted.npz',**{k:v for k,v in result.items() if isinstance(v,np.ndarray)})
    (package/'source/clasts.json').write_text(json.dumps(result['clast_instances']))
    (package/'source/recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    materials=[]
    for material in recipe['materials']:
        kind=material['kind'];material['seed']=recipe['seed']
        maps=author_material(material,recipe['master_resolution'])
        paths={}
        for name,values in maps.items():
            path=package/f'textures/{kind}-{name}.png'
            if name=='height':
                low=float(values.min());extent=max(float(np.ptp(values)),1e-6)
                Image.fromarray(np.uint16(np.clip((values-low)/extent,0,1)*65535)).save(path)
                material.update(height_min_m=low,height_range_m=extent,height_zero=float(-low/extent))
            else:
                if name=='normal':values=values*.5+.5
                Image.fromarray(np.uint8(np.clip(values,0,1)*255)).save(path)
            paths[name]=str(path.relative_to(package))
        materials.append({**material,'maps':paths,'normal_convention':'opengl-positive-y'})
    manifest.update(recipe=recipe,feature_scale_m=recipe['feature_scale_m'],materials=materials,
                    placement_statistics=result['placement_statistics'])
    manifest['artistic_departures']=[{'kind':'height-shaping','gain':recipe['height_gain'],
                                    'fold_amplitude_m':recipe['fold_amplitude_m']}]
    manifest['files']=sorted(str(p.relative_to(package)) for p in package.rglob('*')
                             if p.is_file() and p.name not in ['manifest.json','.terrain-style-package'])
    write_package(package,manifest)
    print(f'Authored {len(result["clast_instances"])} sculpted clasts and {len(materials)} material masters')


def author(package,recipe_path='configs/style-materials.json'):
    package=Path(package)
    with package_stage(package) as stage:
        shutil.copytree(package,stage,dirs_exist_ok=True)
        _author(stage,recipe_path)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--package',default='data/style-patch')
    args=parser.parse_args();author(args.package)
