"""Coherent material height, normals and PBR fields, kept in physical units."""
import numpy as np
from scipy.ndimage import gaussian_filter
from bake.style.surface import noise


def normal_from_height(height,spacing_m):
    south,east=np.gradient(height,spacing_m)
    normal=np.stack([-east,south,np.ones_like(east)],axis=-1)
    return (normal/np.linalg.norm(normal,axis=-1,keepdims=True)).astype('float32')


def author_material(recipe,resolution):
    span=recipe['span_m'];seed=recipe.get('seed',4271)
    axis=np.arange(resolution,dtype='float32')*span/resolution
    x,y=np.meshgrid(axis,axis)
    warp=noise(x/17,y/17,seed)*6
    broad=noise((x+warp)/9,(y-warp)/9,seed+1)
    fine=noise(x/.9,y/.9,seed+2)
    pores=noise(x/2.4,y/2.4,seed+9)
    if recipe['kind']=='granular':
        height=np.zeros((resolution,resolution),dtype='float32')
        rng=np.random.default_rng(seed)
        # Several overlapping sizes, cavities and empty pockets; no Voronoi grid.
        for _ in range(470):
            cx,cy=rng.uniform(0,span,2);r=np.clip(rng.lognormal(.1,.6),.4,5)
            dx=np.minimum(abs(x-cx),span-abs(x-cx));dy=np.minimum(abs(y-cy),span-abs(y-cy))
            dome=np.maximum(1-(dx/r)**2-(dy/(r*rng.uniform(.6,1.3)))**2,0)**.7
            height=np.maximum(height,dome*r*rng.uniform(.35,.65))
        height+=(broad-.5)*.3+(fine-.5)*.12
        color=np.array([.27,.25,.215])[None,None,:]*(.7+.5*broad[:,:,None])
        roughness=.8+.15*pores
    else:
        crease=np.maximum(.16-abs(np.sin(y*.9+warp*2+x*.08)),0)*1.5
        height=broad*.8+fine*.08-crease
        color=np.array([.58,.43,.265])[None,None,:]*(.85+.22*broad[:,:,None])
        roughness=.55+.25*pores
    normal=normal_from_height(height,span/resolution)
    cavity=np.clip((gaussian_filter(height,2,mode='wrap')-height)*1.3,0,.65)
    return {'base_color':np.clip(color,0,1).astype('float32'),'height':height.astype('float32'),
            'normal':normal,'roughness':roughness.astype('float32'),
            'ao':(1-cavity).astype('float32'),'id':np.full(height.shape,recipe['kind']=='granular',dtype='float32')}
