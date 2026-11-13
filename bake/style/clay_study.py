"""Continuous physical clay study: fused crust, worn flanks and incised runnels.

A material/shape calibration specimen, not a replacement for geospatial terrain.
All geometry is authored in metres. Colour contains no baked illumination.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
from bake.style.maps import normal_from_height


def author_study(resolution=1200, seed=5143):
    span=1.2; spacing=span/(resolution-1)
    axis=np.linspace(-span/2,span/2,resolution,dtype='float32');x,y=np.meshgrid(axis,axis)
    rng=np.random.default_rng(seed)
    def noise(scale):
        n=gaussian_filter(rng.random(x.shape),scale/spacing,mode='reflect')
        return ((n-n.min())/max(float(np.ptp(n)),1e-8)).astype('float32')
    cloud=noise(.035); mottling=noise(.012); fine=noise(.0012)
    centre=.028*np.sin(y*7)+.018*np.sin(y*16+.4)
    channel_distance=abs(x-centre)
    macro=np.full(x.shape,.006,dtype='float32')
    for side,phase in [(-1,.3),(1,2.8)]:
        spine=centre+side*(.19+.022*np.sin(y*15+phase)+.015*np.sin(y*28+phase))
        d=x-spine
        width=np.where(d*side>0,.27,.17)
        # Rounded crests with long concave flanks and uneven ridge continuity.
        profile=np.maximum(1-np.sqrt(d*d+.00006)/width,0)**1.65
        height=.115+.024*np.sin(y*13+phase)+.018*np.sin(y*26+phase)
        ridge=height*profile
        macro=np.maximum(macro,ridge+.006)
    # Worn vertical grooves follow the local downhill direction on the banks.
    dx=(x-centre)
    stripe=.5+.5*np.sin((y+.003*np.sin(x*60))*450+np.sin(y*31)*1.4)
    flank=np.clip((channel_distance-.07)/.035,0,1)*np.clip((.23-channel_distance)/.06,0,1)
    wear=.0014*stripe**7*flank
    macro-=wear
    sy,sx=np.gradient(macro,spacing);slope=np.hypot(sx,sy)
    slope_band=np.clip((slope-.18)/.35,0,1)
    clusters=np.clip((cloud-.37)*4,0,1)
    crust_mask=clusters*slope_band*np.clip((channel_distance-.055)/.04,0,1)
    aggregate=np.zeros_like(macro)
    # The nodules belong to the continuous height surface. No floating objects.
    for count,rmin,rmax in [(12500,.0018,.0065),(9000,.0007,.0022)]:
        for _ in range(count):
            cx,cy=rng.uniform(-span/2,span/2,2)
            col=int((cx+span/2)/spacing);row=int((cy+span/2)/spacing)
            if rng.random()>crust_mask[row,col]:continue
            radius=rng.uniform(rmin,rmax)
            extent=max(2,int(np.ceil(radius/spacing*1.2)))
            c0=max(0,col-extent);c1=min(resolution,col+extent+1)
            r0=max(0,row-extent);r1=min(resolution,row+extent+1)
            u=(x[r0:r1,c0:c1]-cx)/radius
            v=(y[r0:r1,c0:c1]-cy)/(radius*rng.uniform(.65,1.25))
            dome=np.maximum(1-u*u-v*v,0)**.7
            dome*=radius*rng.uniform(.35,.75)
            # A small fused shoulder rounds intersecting grains without plates.
            current=aggregate[r0:r1,c0:c1]
            blend=np.maximum(.0005-abs(current-dome),0)/.0005
            aggregate[r0:r1,c0:c1]=np.maximum(current,dome)+blend*blend*.000125*(dome>0)
    aggregate=gaussian_filter(aggregate,.3)
    pores=(fine-.5)*.0003
    height=macro+aggregate+pores
    crust=np.clip(gaussian_filter(aggregate,.0015/spacing)*600,0,1)*crust_mask
    dust=np.clip((mottling-.45)*2,0,1)
    worn=np.clip((macro-.09)/.05,0,1)*(1-crust)
    clay=np.array([.235,.205,.165],dtype='float32')
    ochre=np.array([.37,.245,.105],dtype='float32')
    charcoal=np.array([.09,.085,.071],dtype='float32')
    colour=clay[None,None,:]*(1-worn[:,:,None]*.6)+ochre[None,None,:]*worn[:,:,None]*.6
    colour=colour*(1-crust[:,:,None]) + charcoal[None,None,:]*crust[:,:,None]
    colour*=.94+.12*mottling[:,:,None]
    colour+=dust[:,:,None]*np.array([.028,.025,.018],dtype='float32')
    roughness=np.clip(.57+.31*crust+.08*dust-.09*(channel_distance<.065),.44,.94)
    return {'height':height.astype('float32'),'base_color':colour.astype('float32'),
        'roughness':roughness.astype('float32'),'normal':normal_from_height(height,spacing),
        'aggregate_height':aggregate,'crust':crust.astype('float32'),'dust':dust.astype('float32')}


def write_study(output,resolution):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    maps=author_study(resolution);np.savez_compressed(output/'surface.npz',**maps)
    c=maps['base_color'];srgb=np.where(c<=.0031308,12.92*c,1.055*c**(1/2.4)-.055)
    Image.fromarray(np.uint8(np.clip(srgb,0,1)*255)).save(output/'base-color.png')
    Image.fromarray(np.uint8((maps['normal']*.5+.5)*255)).save(output/'surface-normal.png')
    for key in ['roughness','crust','dust']:
        Image.fromarray(np.uint8(maps[key]*255)).save(output/f'{key}.png')
    lo,hi=float(maps['height'].min()),float(maps['height'].max())
    Image.fromarray(np.uint16((maps['height']-lo)/(hi-lo)*65535)).save(output/'height.png')
    (output/'manifest.json').write_text(json.dumps({'kind':'physical clay calibration study',
        'span_m':1.2,'seed':5143,'resolution':resolution,'height_range_m':[lo,hi],
        'colour_space':'base colour PNG sRGB; remaining images linear data',
        'note':'Not San Luis terrain. Full normal includes macro shape; do not double-apply on full geometry.'},indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resolution',type=int,default=1200)
    args=parser.parse_args();write_study(args.output,args.resolution)
