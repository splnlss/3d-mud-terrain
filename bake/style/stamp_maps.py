"""Convert linear geometry data into portable material images without lighting."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def convert(directory):
    directory = Path(directory)
    data = np.load(directory/'maps.npz')
    height, normal, ao = (data[key] for key in ('height','normal','ao'))
    if not all(np.isfinite(a).all() for a in (height,normal,ao)):
        raise ValueError('Non-finite stamp data')
    decoded = normal*2-1
    decoded /= np.maximum(np.linalg.norm(decoded,axis=-1,keepdims=True),1e-6)
    Image.fromarray(np.uint8(np.clip(decoded*.5+.5,0,1)*255)).save(directory/'normal.png')
    Image.fromarray(np.uint8(np.clip(ao,0,1)*255)).save(directory/'ao.png')
    low, high = float(height.min()),float(height.max())
    Image.fromarray(np.uint16(np.clip((height-low)/max(high-low,1e-6),0,1)*65535)).save(directory/'height.png')
    height.astype('<f4').tofile(directory/'height.f32')
    roughness = np.clip(.95-.30*(height-low)/max(high-low,1e-6),0,1)
    orm = np.stack((ao,roughness,np.zeros_like(ao)),axis=-1)
    Image.fromarray(np.uint8(np.clip(orm,0,1)*255)).save(directory/'orm.png')
    manifest = json.loads((directory/'manifest.json').read_text())
    manifest['portable_maps'] = {'normal':'normal.png','height':'height.png','height_float':'height.f32',
        'height_decode':{'offset_m':low,'range_m':high-low},'occlusion_roughness_metallic':'orm.png',
        'colour_space':'linear data; no photographic shading'}
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {'height_range_m':[low,high], 'ao_range':[float(ao.min()),float(ao.max())], 'shape':list(height.shape)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    print(convert(parser.parse_args().directory))
