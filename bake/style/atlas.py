"""Bake material composition into portable unique-UV atlas fields."""
import numpy as np
from scipy.ndimage import map_coordinates,gaussian_filter
from bake.style.surface import noise
from bake.style.maps import normal_from_height


def compose_atlas(bounds,resolution,recipe,crust):
    west,south,east,north=bounds
    x,y=np.meshgrid(np.linspace(west,east,resolution),np.linspace(north,south,resolution))
    seed=recipe.get('seed',4271)
    broad=noise(x/27,y/27,seed);warp=noise(x/14,y/14,seed+3)*3
    grain=noise(x/.6,y/.6,seed+5)
    clumps=(1-abs(2*noise((x+warp)/2.3,(y-warp)/2.3,seed+1)-1))**3
    grooves=np.maximum(.13-abs(np.sin(y*1.2+warp*2+x*.08)),0)
    indices=np.meshgrid(np.linspace(0,crust.shape[1]-1,resolution),np.linspace(0,crust.shape[0]-1,resolution))
    weight=map_coordinates(crust,[indices[1],indices[0]],order=1)
    weight=np.clip((weight-.25)*1.8+(broad-.5)*.6,0,1)
    fine_height=weight*(broad*.5-grooves*.75+(grain-.5)*.08)+(1-weight)*(clumps*.8+(grain-.5)*.18)
    normal=normal_from_height(fine_height,(east-west)/(resolution-1))
    ochre=np.array([.67,.54,.36]);dark=np.array([.32,.30,.26]);dust=np.array([.73,.69,.60])
    color=dark+(ochre-dark)*weight[:,:,None]
    color*=.83+.22*broad[:,:,None]
    color=color*(1-.18*grain[:,:,None])+dust*.18*grain[:,:,None]
    cavity=np.maximum(gaussian_filter(fine_height,2)-fine_height,0)
    return {'base_color':color.astype('float32'),'normal':normal,
            'height':fine_height.astype('float32'),'roughness':(.9-.23*weight+.06*grain).astype('float32'),
            'ao':np.clip(1-cavity*.8,.5,1).astype('float32'),
            'uv_surface_metric':{'metres_per_uv':[east-west,north-south],
                                 'projection':'planar-east-north','requires_surface_jacobian':True}}
