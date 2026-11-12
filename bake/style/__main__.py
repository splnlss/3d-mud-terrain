"""Build a portable style patch from cached source data; no network required."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from rasterio.warp import transform_geom
from shapely.geometry import shape,box,mapping
from shapely.ops import transform as geometry_transform
from bake.style.patch import read_patch,file_hash
from bake.style.package import package_stage,write_package
from bake.shape import shape_dem


def hillshade(heights,spacing):
    south,east=np.gradient(heights,spacing)
    n=np.stack([-east,np.ones_like(east),-south],axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    light=np.maximum(n@np.array([.6,.7,.4]),0)
    h=(heights-heights.min())/max(float(np.ptp(heights)),1)
    base=np.stack([.36+.38*h,.35+.28*h,.29+.16*h],axis=-1)
    return Image.fromarray(np.uint8(np.clip(base*(.45+.55*light[:,:,None]),0,1)*255)).resize((1000,1000))


def build(config_path,output):
    config=json.loads(Path(config_path).read_text())
    for name in ['dem','hydrography']:
        path=Path(config[name])
        if not path.is_file():raise ValueError(f'Missing {path}; run npm run bake:scene to populate cached GIS inputs')
        expected=config['source_hashes'][name]
        if file_hash(path)!=expected:raise ValueError(f'{name} hash differs from selected patch source; inspect source before updating config')
    heights,metadata=read_patch(Path(config['dem']),tuple(config['center_utm_m']),config['size_m'])
    cx,cy=metadata['origin_utm_m'];half=config['size_m']/2
    features=[];hydro=json.loads(Path(config['hydrography']).read_text())
    bounds=box(cx-half,cy-half,cx+half,cy+half)
    for f in hydro['layers']['6']:
        if f['properties'].get('gnis_name') not in config['water_names']:continue
        world=shape(transform_geom('EPSG:4326',metadata['source_crs'],f['geometry']))
        clipped=world.intersection(bounds)
        if not clipped.is_empty:
            local=geometry_transform(lambda x,y,z=None:(np.asarray(x)-cx,cy-np.asarray(y)),clipped)
            features.append({'type':'Feature','properties':f['properties'],'geometry':mapping(local)})
    if not features:raise ValueError('selected patch contains no required mapped channel')
    with package_stage(output) as stage:
        for name in ['source','meshes','textures','height','review']:(stage/name).mkdir()
        np.save(stage/'source/dem.npy',heights)
        (stage/'source/water.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
        (stage/'source/config.json').write_text(json.dumps(config,indent=2)+'\n')
        hillshade(heights,metadata['spacing_m']).save(stage/'review/source-terrain.png')
        overlay=hillshade(heights,metadata['spacing_m']);draw=ImageDraw.Draw(overlay)
        for f in features:
            geom=shape(f['geometry'])
            for line in geom.geoms if geom.geom_type=='MultiLineString' else [geom]:
                draw.line([((x+half)/config['size_m']*999,(z+half)/config['size_m']*999) for x,z,*_ in line.coords],fill='#ede0c6',width=5)
        overlay.save(stage/'review/source-overlay.png')
        legacy=shape_dem(heights.copy(),config['size_m'],float(heights.min()),edge_width=0,rounding_sigma=6,amplitude=60)
        hillshade(legacy,metadata['spacing_m']).save(stage/'review/legacy-top-shading.png')
        base=float(heights.min())
        metadata.update({'schema_version':1,'units':'m','axes':'x-east,y-up,z-south',
             'base_elevation_m':base,'source_hashes':config['source_hashes'],'recipe':{},'materials':[],
             'lods':[],'water':{'source':'source/water.geojson','names':config['water_names']},
             'feature_scale_m':{},'artistic_departures':[],
             'cameras':{'elevated':{'target':[0,100,0],'distance':2800,'yaw_deg':30,'pitch_deg':48,'fov_y_deg':40},
                        'overhead':{'target':[0,100,0],'distance':3200,'yaw_deg':0,'pitch_deg':88,'fov_y_deg':40},
                        'close':{'target':[0,100,0],'distance':1200,'yaw_deg':30,'pitch_deg':28,'fov_y_deg':40}},
             'review_notes':{'baseline':'legacy-top-shading.png is the old shaping recipe shown as diagnostic hillshade, not a browser capture'},
             'files':sorted(str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file())})
        write_package(stage,metadata)
    print(f'Wrote {output}: {heights.shape}, {len(features)} mapped channel features, relief {np.ptp(heights):.1f} m')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/style-patch.json'))
    parser.add_argument('--output',type=Path,default=Path('data/style-patch'))
    args=parser.parse_args()
    try:build(args.config,args.output)
    except (ValueError,FileNotFoundError) as e:parser.exit(2,f'{e}\n')


if __name__=='__main__':main()
