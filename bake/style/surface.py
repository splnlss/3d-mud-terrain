"""Sculpted ridge fields and spatially clustered, reproducible clast instances."""
import math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates
from scipy.spatial.transform import Rotation


def noise(x,y,seed=4271):
    ix=np.floor(x).astype('int64');iy=np.floor(y).astype('int64')
    fx=x-ix;fy=y-iy;fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    def h(dx,dy):
        n=((ix+dx)*374761393+(iy+dy)*668265263+seed)&0xffffffff
        n=((n^(n>>13))*1274126177)&0xffffffff
        return (n^(n>>16))/4294967295
    return (h(0,0)*(1-fx)+h(1,0)*fx)*(1-fy)+(h(0,1)*(1-fx)+h(1,1)*fx)*fy


def placement_spread(points):
    if len(points)<3:return 0.
    d=cKDTree(points).query(points,k=2)[0][:,1]
    return float(d.std()/max(d.mean(),1e-8))


def cluster_layout(bounds,recipe):
    west,south,east,north=bounds
    config=recipe['clusters'];cell=config['cell_m'];seed=recipe['seed']
    clusters=[];instances=[]
    for ix in range(math.floor(west/cell)-1,math.ceil(east/cell)+1):
        for iy in range(math.floor(south/cell)-1,math.ceil(north/cell)+1):
            rng=np.random.default_rng(np.random.SeedSequence([seed,ix&0xffffffff,iy&0xffffffff]))
            if rng.random()>config['probability']:continue
            cx=(ix+rng.uniform(.15,.85))*cell;cy=(iy+rng.uniform(.15,.85))*cell
            rx,rz=rng.uniform(*config['radius_m'],2);angle=rng.uniform(-math.pi,math.pi)
            clusters.append((cx,cy,rx,rz,angle))
            count=round(1.0*rx*rz/100)
            for j in range(count):
                phi=rng.uniform(0,2*math.pi);r=np.sqrt(rng.uniform(0,.78))
                dx,dy=r*rx*np.cos(phi),r*rz*np.sin(phi)
                x=cx+dx*np.cos(angle)-dy*np.sin(angle)
                y=cy+dx*np.sin(angle)+dy*np.cos(angle)
                radius=float(np.clip(rng.lognormal(np.log(8.5),recipe['clasts']['lognormal_sigma']),*recipe['clasts']['radius_m']))
                if not (west-20<=x<=east+20 and south-20<=y<=north+20):continue
                elevation=radius*rng.uniform(*recipe['clasts']['height_radius'])
                rotation=rng.uniform(-math.pi,math.pi)
                instances.append({'id':f'{ix}:{iy}:{j}','position_m':[float(x),0.,float(-y)],
                     'radii_m':[radius,float(elevation),float(radius*rng.uniform(.6,1.15))],
                     'orientation_xyzw':[0.,float(np.sin(rotation/2)),0.,float(np.cos(rotation/2))],
                     'shape_id':f'clast-{j%12}'})
    # Sample actual projected ellipse occupancy; counts alone do not measure coverage.
    step=8.;xx,yy=np.meshgrid(np.arange(west,east,step),np.arange(south,north,step))
    inside=np.zeros(xx.shape,bool);covered=np.zeros(xx.shape,bool)
    for cx,cy,rx,rz,a in clusters:
        dx=xx-cx;dy=yy-cy
        inside|=((dx*np.cos(a)+dy*np.sin(a))/rx)**2+((-dx*np.sin(a)+dy*np.cos(a))/rz)**2<1
    for c in instances:
        x,_,z=c['position_m'];rx,_,rz=c['radii_m']
        rows=np.where(np.abs(yy[:,0]+z)<rx*1.3)[0];cols=np.where(np.abs(xx[0]-x)<rx*1.3)[0]
        if len(rows) and len(cols):
            grid=np.ix_(rows,cols);a=2*np.arctan2(c['orientation_xyzw'][1],c['orientation_xyzw'][3])
            dx=xx[grid]-x;dy=yy[grid]+z
            covered[grid]|=((dx*np.cos(a)+dy*np.sin(a))/rx)**2+((-dx*np.sin(a)+dy*np.cos(a))/rz)**2<1
    stats={'inside_occupancy':float(covered[inside].mean()) if inside.any() else 0.,
           'outside_occupancy':float(covered[~inside].mean()) if (~inside).any() else 0.,
           'placement_spread':placement_spread(np.array([[c['position_m'][0],c['position_m'][2]] for c in instances]))}
    return instances,stats


def sculpt_field(east,north,source,recipe):
    spacing=float(abs(east[0,1]-east[0,0]));base=recipe.get('base_elevation_m',2500)
    dy,dx=np.gradient(source,spacing);slope=np.hypot(dx,dy)
    fine=noise(east/31,north/31,recipe['seed'])
    warp=noise(east/340,north/340,recipe['seed']+3)*65
    folds=(1-np.abs(2*noise((east+warp)/150,(north-warp)/210,recipe['seed']+4)-1))**5
    folds+=.35*(1-np.abs(2*noise((east-warp)/65,(north+warp)/95,recipe['seed']+7)-1))**4
    fold=recipe['fold_amplitude_m']*(folds-.4)*np.clip(slope*3+.2,0,1)
    height=base+(source-base)*recipe['height_gain']+fold
    curvature=np.gradient(dx,spacing,axis=1)+np.gradient(dy,spacing,axis=0)
    crust=np.clip(.85-slope*1.7+curvature*8+(fine-.5)*.65,0,1)
    instances,stats=cluster_layout((east.min(),north.min(),east.max(),north.max()),recipe)
    retained=[]
    shaped_south,shaped_east=np.gradient(height,spacing)
    for c in instances:
        x,_,z=c['position_m'];row=int(np.clip(round((north.max()+z)/spacing),0,len(source)-1))
        col=int(np.clip(round((x-east.min())/spacing),0,source.shape[1]-1))
        # Broad slope/aspect weighting leaves exposed convex clay between deposits.
        probability=np.clip(.22+recipe['placement']['slope_weight']*slope[row,col]*2
                            +recipe['placement']['concavity_weight']*max(-curvature[row,col]*80,0)
                            +recipe['placement']['shaded_aspect_weight']*max(-dx[row,col],0),.15,.95)
        key=sum(ord(ch) for ch in c['id'])
        if noise(np.array(x/11),np.array(-z/11),key)>probability:continue
        coords=np.array([[(north.max()+z)/spacing],[(x-east.min())/spacing]])
        elevation=float(map_coordinates(height,coords,order=1,mode='nearest')[0])
        surface_n=np.array([-shaped_east[row,col],1.,-shaped_south[row,col]])
        surface_n/=np.linalg.norm(surface_n)
        axis=np.cross([0,1,0],surface_n);q=np.r_[axis,1+surface_n[1]];q/=np.linalg.norm(q)
        rotation=Rotation.from_quat(q)*Rotation.from_quat(c['orientation_xyzw'])
        c['orientation_xyzw']=rotation.as_quat().tolist()
        c['position_m'][1]=elevation+c['radii_m'][1]*.08
        retained.append(c)
    return {'height':height.astype('float32'),'crust':crust.astype('float32'),
            'cluster':(1-crust).astype('float32'),'dust':np.clip(.6-slope,0,1).astype('float32'),
            'cavity':np.clip(-curvature*40,0,1).astype('float32'),
            'clast_instances':retained,'placement_statistics':stats}
