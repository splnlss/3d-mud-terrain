"""Periodic fused clay relief and independently authored physical finish maps.

No colour-image brightness is interpreted as geometry. All scale is in metres.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image


def author_granular(resolution=1024, span_m=32, seed=9261):
    rng = np.random.default_rng(seed)
    spacing = span_m/resolution
    def field(scale):
        value = gaussian_filter(rng.random((resolution,resolution)),scale/spacing,mode='wrap')
        return (value-value.min())/max(float(np.ptp(value)),1e-6)
    broad = field(1.3); dust = field(.45); pores = field(.045)
    height = .08*broad + .035*pores
    # Overlapping rounded, asymmetric lobes are fused into a matrix. No plate grid.
    for count,minimum,maximum,rise in [(650,.25,1.2,.36),(4200,.055,.3,.32)]:
        count = int(count*(span_m/32)**2)
        for _ in range(count):
            cx,cy = rng.uniform(0,resolution,2)
            radius = rng.uniform(minimum,maximum)
            extent = int(np.ceil(radius/spacing*1.3))
            ix = np.arange(int(cx)-extent,int(cx)+extent+1)
            iy = np.arange(int(cy)-extent,int(cy)+extent+1)
            x = (ix-cx)*spacing/radius; y = (iy-cy)*spacing/(radius*rng.uniform(.7,1.2))
            radial = y[:,None]**2+x[None,:]**2
            dome = np.maximum(1-radial,0)**.75*radius*rise
            rows,cols = np.ix_(iy%resolution,ix%resolution)
            existing = height[rows,cols]
            surface = .03 + dome
            # Smooth maximum with a short transition fuses intersecting lobes.
            blend = np.maximum(.025-np.abs(existing-surface),0)/.025
            height[rows,cols] = np.maximum(existing,surface)+blend*blend*.00625
    height += (pores-.5)*.018
    east = (np.roll(height,-1,1)-np.roll(height,1,1))/(2*spacing)
    south = (np.roll(height,-1,0)-np.roll(height,1,0))/(2*spacing)
    normal = np.stack([-east,south,np.ones_like(height)],axis=-1)
    normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
    cavity = np.clip((gaussian_filter(height,.2/spacing,mode='wrap')-height)*9,0,.65)
    wet = np.clip((broad-.44)*3,0,1)
    roughness = np.clip(.91-.53*wet+.035*(pores-.5)+.05*dust,.28,.96)
    return {key: value.astype('float32') for key,value in
            {'height':height,'normal':normal,'ao':1-cavity,'roughness':roughness,'dust':dust,'wetness':wet}.items()}


def write_material(output,resolution=1024):
    output = Path(output); output.mkdir(parents=True,exist_ok=True)
    maps = author_granular(resolution=resolution)
    np.savez_compressed(output/'maps.npz',**maps)
    height = maps['height']; lo,hi = float(height.min()),float(height.max())
    Image.fromarray(np.uint16((height-lo)/(hi-lo)*65535)).save(output/'height.png')
    Image.fromarray(np.uint8((maps['normal']*.5+.5)*255)).save(output/'normal.png')
    for name in ('roughness','ao','dust','wetness'):
        Image.fromarray(np.uint8(np.clip(maps[name],0,1)*255)).save(output/f'{name}.png')
    orm = np.stack([maps['ao'],maps['roughness'],np.zeros_like(height)],axis=-1)
    Image.fromarray(np.uint8(orm*255)).save(output/'orm.png')
    (output/'manifest.json').write_text(json.dumps({'seed':9261,'span_m':32,'resolution':resolution,
        'height_range_m':[lo,hi],'normal_convention':'OpenGL +Y, periodic central derivatives',
        'ao':'local cavity approximation; not ray-traced','roughness_range':[float(maps['roughness'].min()),float(maps['roughness'].max())],
        'source':'authored fused granular height field, independent of albedo'},indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resolution',type=int,default=1024)
    args = parser.parse_args();write_material(args.output,args.resolution)
