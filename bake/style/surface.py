"""Sculpted ridge fields and spatially clustered, reproducible clast instances."""
import math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import map_coordinates,gaussian_filter
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
            count=round(rx*rz/config.get('count_radius_squared',100))
            for j in range(count):
                phi=rng.uniform(0,2*math.pi);r=np.sqrt(rng.uniform(0,.78))
                dx,dy=r*rx*np.cos(phi),r*rz*np.sin(phi)
                x=cx+dx*np.cos(angle)-dy*np.sin(angle)
                y=cy+dx*np.sin(angle)+dy*np.cos(angle)
                radius=float(np.clip(rng.lognormal(np.log(recipe['clasts'].get('median_radius_m',8.5)),recipe['clasts']['lognormal_sigma']),*recipe['clasts']['radius_m']))
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


def clay_stamps(east,north,recipe):
    """Asymmetric overlapping clay masses, stable in a global coordinate frame."""
    result=np.zeros_like(east);config=recipe.get('clay_mass',{'cell_m':160,'radius_m':[45,115],'height_m':[35,85]});cell=config['cell_m'];seed=recipe['seed']+71
    for ix in range(math.floor(float(east.min())/cell)-1,math.ceil(float(east.max())/cell)+1):
        for iy in range(math.floor(float(north.min())/cell)-1,math.ceil(float(north.max())/cell)+1):
            rng=np.random.default_rng(np.random.SeedSequence([seed,ix&0xffffffff,iy&0xffffffff]))
            cx=(ix+rng.uniform(.1,.9))*cell;cy=(iy+rng.uniform(.1,.9))*cell
            rx,ry=rng.uniform(*config['radius_m'],2);angle=rng.uniform(-math.pi,math.pi)
            dx=east-cx;dy=north-cy
            u=(dx*np.cos(angle)+dy*np.sin(angle))/rx;v=(-dx*np.sin(angle)+dy*np.cos(angle))/ry
            distortion=(noise((east+ix*17)/18,(north+iy*31)/18,seed)-.5)*.18
            distortion+=(noise(east/7,north/7,seed+9)-.5)*.06
            # Distance to a short bent ridge segment, not an elliptical dome.
            spine=.16*np.sin(u*3+ix)+.08*np.sin(u*7+iy)
            end=np.maximum(np.abs(u)-.4,0)/.65
            radius=np.sqrt(end*end+((v-spine)/.8)**2)+distortion
            dome=np.maximum(1-radius,0)**1.35
            # A pinched shoulder and unequal crest avoid uniform hemispheres.
            shoulder=1+.16*np.sin(3*np.arctan2(v,u)+ix)*np.sqrt(np.clip(u*u+v*v,0,1))-.12*u
            stamp=dome*shoulder*rng.uniform(*config['height_m'])
            k=5.;overlap=np.clip(1-np.abs(result-stamp)/k,0,1)**2*k*.25
            overlap*=np.clip(np.minimum(result,stamp)/k,0,1)
            result=np.maximum(result,stamp)+overlap
    return result


def crust_instances(east,north,height,crust,south_gradient,east_gradient,recipe):
    config=recipe.get('crust_nodules')
    if not config:return []
    cell=config['cell_m'];seed=recipe['seed']+300;spacing=east[0,1]-east[0,0]
    ix,iy=np.meshgrid(np.arange(math.floor(east.min()/cell),math.ceil(east.max()/cell)),
                       np.arange(math.floor(north.min()/cell),math.ceil(north.max()/cell)))
    x=(ix+.1+.8*noise(ix,iy,seed))*cell;y=(iy+.1+.8*noise(ix,iy,seed+1))*cell
    coords=np.array([(north.max()-y.ravel())/spacing,(x.ravel()-east.min())/spacing])
    weights=map_coordinates(crust,coords,order=1,mode='nearest')
    sx=map_coordinates(east_gradient,coords,order=1,mode='nearest')
    sy=map_coordinates(south_gradient,coords,order=1,mode='nearest')
    choose=(np.hypot(sx,sy)>config['slope_min'])&(noise(ix,iy,seed+2).ravel()<(1-weights)*config['density'])
    coords=coords[:,choose];sx=sx[choose];sy=sy[choose]
    x=x.ravel()[choose];y=y.ravel()[choose];ix=ix.ravel()[choose];iy=iy.ravel()[choose]
    # Hash-derived size remains identical when this world region is cropped.
    random=noise(ix,iy,seed+3);radius=np.clip(config['median_radius_m']*np.exp((random-.5)*1.2),*config['radius_m'])
    low,high=config.get('height_radius',[.35,.55])
    vertical=radius*(low+(high-low)*noise(ix,iy,seed+4))
    nz=np.ones_like(sx);normals=np.c_[-sx,nz,-sy];normals/=np.linalg.norm(normals,axis=1,keepdims=True)
    axes=np.cross(np.array([0,1,0]),normals);q=np.c_[axes,1+normals[:,1]];q/=np.linalg.norm(q,axis=1,keepdims=True)
    yaw=np.c_[np.zeros(len(x)),noise(ix,iy,seed+5)*2*math.pi,np.zeros(len(x))]
    rotations=(Rotation.from_quat(q)*Rotation.from_rotvec(yaw)).as_quat()
    elevations=map_coordinates(height,coords,order=1,mode='nearest')+vertical*config.get('embedding_height_fraction',-.05)
    return [{'id':f'crust:{a}:{b}','position_m':[float(cx),float(h),float(-cy)],
             'radii_m':[float(r),float(v),float(r*.85)],'orientation_xyzw':rotation.tolist(),
             'shape_id':f'clast-{(int(a)*7+int(b)*13)%12}','band':'crust'}
            for a,b,cx,cy,h,r,v,rotation in zip(ix,iy,x,y,elevations,radius,vertical,rotations)]


def sculpt_field(east,north,source,recipe):
    spacing=float(abs(east[0,1]-east[0,0]));base=recipe.get('base_elevation_m',2500)
    dy,dx=np.gradient(source,spacing);slope=np.hypot(dx,dy)
    fine=noise(east/31,north/31,recipe['seed'])
    warp=noise(east/340,north/340,recipe['seed']+3)*65
    folds=(1-np.abs(2*noise((east+warp)/150,(north-warp)/210,recipe['seed']+4)-1))**5
    folds+=.35*(1-np.abs(2*noise((east-warp)/65,(north+warp)/95,recipe['seed']+7)-1))**4
    fold=recipe['fold_amplitude_m']*(folds-.4)*np.clip(slope*3+.2,0,1)
    height=base+(source-base)*recipe['height_gain']+fold
    if recipe.get('clay_stamps',False):height+=clay_stamps(east,north,recipe)
    grain=recipe.get('surface_grain')
    if grain:
        height+=grain['amplitude_m']*(.65*noise(east/grain['wavelength_m'][1],north/grain['wavelength_m'][1],recipe['seed']+90)
                 +.35*noise(east/grain['wavelength_m'][0],north/grain['wavelength_m'][0],recipe['seed']+91)-.5)
    striation=recipe.get('striation')
    if striation:
        macro=gaussian_filter(height,max(1,12/spacing))
        sy,sx=np.gradient(macro,spacing);length=np.maximum(np.hypot(sx,sy),.05)
        across=(-sy*east-sx*north)/length/striation['across_m']
        grooves=noise(across,macro/striation['along_height_m'],recipe['seed']+120)
        height-=striation['depth_m']*np.maximum(.6-grooves,0)*np.clip(length,0,1)
        period=striation['shelf_period_m'];offset=noise(east/30,north/30,recipe['seed']+121)*period*.45
        phase=(height+offset)/period;fraction=phase-np.floor(phase)
        height+=period*(fraction*fraction*(3-2*fraction)-fraction)*np.clip(length*.8,0,1)
    macro=gaussian_filter(height,max(1,18/spacing))
    dy,dx=np.gradient(macro,spacing);slope=np.hypot(dx,dy)
    curvature=np.gradient(dx,spacing,axis=1)+np.gradient(dy,spacing,axis=0)
    aspect=(-dx*.6+.5+dy*.3)/np.sqrt(1+slope*slope)
    crust=np.clip(.96-slope*.85-curvature*12+(fine-.5)*.4+aspect*.12,0,1)
    aggregate=noise(east/4.5+noise(east/27,north/27,recipe['seed']+180)*2,north/5.5,recipe['seed']+181)
    matrix=np.clip((aggregate-.35)*1.8,0,1)**1.25
    height+=recipe.get('aggregate_relief_m',0)*matrix*(1-crust)
    instances,stats=cluster_layout((east.min(),north.min(),east.max(),north.max()),recipe)
    retained=[]
    shaped_south,shaped_east=np.gradient(height,spacing)
    shaped_curvature=np.gradient(shaped_east,spacing,axis=1)+np.gradient(shaped_south,spacing,axis=0)
    shaped_slope=np.hypot(shaped_east,shaped_south)
    for c in instances:
        x,_,z=c['position_m'];row=int(np.clip(round((north.max()+z)/spacing),0,len(source)-1))
        col=int(np.clip(round((x-east.min())/spacing),0,source.shape[1]-1))
        # Broad slope/aspect weighting leaves exposed convex clay between deposits.
        probability=np.clip(.35+recipe['placement']['slope_weight']*shaped_slope[row,col]
                            +recipe['placement']['concavity_weight']*max(shaped_curvature[row,col]*20,0)
                            +recipe['placement']['shaded_aspect_weight']*max(-shaped_east[row,col],0)-recipe['placement']['convex_exposure_weight']*max(-shaped_curvature[row,col]*12,0),.1,.95)
        key=sum(ord(ch) for ch in c['id'])
        if noise(np.array(x/11),np.array(-z/11),key)>probability:continue
        coords=np.array([[(north.max()+z)/spacing],[(x-east.min())/spacing]])
        elevation=float(map_coordinates(height,coords,order=1,mode='nearest')[0])
        surface_n=np.array([-shaped_east[row,col],1.,-shaped_south[row,col]])
        surface_n/=np.linalg.norm(surface_n)
        axis=np.cross([0,1,0],surface_n);q=np.r_[axis,1+surface_n[1]];q/=np.linalg.norm(q)
        rotation=Rotation.from_quat(q)*Rotation.from_quat(c['orientation_xyzw'])
        c['orientation_xyzw']=rotation.as_quat().tolist()
        c['position_m'][1]=elevation+c['radii_m'][1]*recipe['clasts'].get('embedding_height_fraction',-.3)
        retained.append(c)
    retained+=crust_instances(east,north,height,crust,shaped_south,shaped_east,recipe)
    return {'height':height.astype('float32'),'crust':crust.astype('float32'),
            'cluster':(1-crust).astype('float32'),'dust':np.clip(.6-slope,0,1).astype('float32'),
            'cavity':np.clip(curvature*40,0,1).astype('float32'),
            'clast_instances':retained,'placement_statistics':stats}
