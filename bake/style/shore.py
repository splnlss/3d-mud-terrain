"""Canonical mapped water and supported, feathered clay banks for the style patch."""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import distance_transform_edt,map_coordinates,gaussian_filter,zoom
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from rasterio.features import rasterize
from rasterio.transform import from_origin
import mapbox_earcut


def support_shore(ground,surface,inside,spacing_m,bank_width_m):
    distance=distance_transform_edt(~inside)*spacing_m
    amount=np.clip(1-distance/bank_width_m,0,1)
    blend=amount*amount*(3-2*amount)
    target=surface+distance*.65
    shaped=ground*(1-blend)+target*blend
    bed_depth=np.minimum(distance_transform_edt(inside)*spacing_m*1.2,8)
    shaped=np.where(inside,surface-bed_depth,shaped)
    return shaped.astype('float32'),blend.astype('float32')


def integrate_shore(package,half_width_m=30):
    package=Path(package);m=json.loads((package/'manifest.json').read_text())
    source=np.load(package/'source/dem.npy');fields=dict(np.load(package/'source/sculpted.npz'))
    # A 2.5 m authored mesh resolves the bank lip and fold profile; source DEM stays 10 m.
    factor=4;count=(source.shape[0]-1)*factor+1
    cols,rows=np.meshgrid(np.linspace(0,source.shape[1]-1,count),np.linspace(0,source.shape[0]-1,count))
    for key,value in fields.items():
        ratio=(value.shape[0]-1)/(source.shape[0]-1)
        fields[key]=map_coordinates(value,[rows*ratio,cols*ratio],order=1,mode='nearest')
    size=m['size_m'];spacing=size/(count-1);half=size/2
    x,z=np.meshgrid(np.linspace(-half,half,count),np.linspace(-half,half,count))
    lines=[shape(f['geometry']) for f in json.loads((package/'source/water.geojson').read_text())['features']]
    channel=unary_union(lines);polygon=channel.buffer(half_width_m,quad_segs=5)
    # GeoJSON coordinates are x-east,z-south; raster transform's y direction is reversed.
    from shapely import transform
    north_polygon=transform(polygon,lambda coords:coords*np.array([1,-1]))
    north_line=transform(channel,lambda coords:coords*np.array([1,-1]))
    transform_grid=from_origin(-half-spacing/2,half+spacing/2,spacing,spacing)
    inside=rasterize([(north_polygon,1)],out_shape=(count,count),transform=transform_grid).astype(bool)
    centre=rasterize([(north_line,1)],out_shape=(count,count),transform=transform_grid,all_touched=True).astype(bool)
    indices=distance_transform_edt(~centre,return_distances=False,return_indices=True)
    smooth_source=gaussian_filter(source,1.5)
    river_source=map_coordinates(smooth_source,[rows,cols],order=1)
    gain=m['recipe']['height_gain'];base=m['base_elevation_m']
    river_surface=base+(river_source-base)*gain
    surface=river_surface[tuple(indices)]
    surface=gaussian_filter(surface,2)
    fields['height'],band=support_shore(fields['height'],surface,inside,spacing,45)
    fields['wet_band']=band
    # Pale silty bank margins and suppressed dark carpet around contact.
    fields['crust']=np.maximum(fields['crust'],band*.8)
    fields['dust']=np.maximum(fields['dust'],band*.6)
    clasts=json.loads((package/'source/clasts.json').read_text());retained=[]
    south_grad,east_grad=np.gradient(fields['height'],spacing)
    from scipy.spatial.transform import Rotation
    for c in clasts:
        cx,cy,cz=c['position_m'];r=(cz+half)/spacing;col=(cx+half)/spacing
        ri,ci=int(np.clip(round(r),0,count-1)),int(np.clip(round(col),0,count-1))
        if inside[ri,ci] or band[ri,ci]>.85:continue
        c['position_m'][1]=float(map_coordinates(fields['height'],[[r],[col]],order=1,mode='nearest')[0]+c['radii_m'][1]*(m['recipe']['crust_nodules'].get('embedding_height_fraction',-.05) if c.get('band')=='crust' else m['recipe']['clasts'].get('embedding_height_fraction',-.3)))
        if band[ri,ci]>0:
            n=np.array([-east_grad[ri,ci],1.,-south_grad[ri,ci]]);n/=np.linalg.norm(n)
            axis=np.cross([0,1,0],n);q=np.r_[axis,1+n[1]];q/=np.linalg.norm(q)
            c['orientation_xyzw']=Rotation.from_quat(q).as_quat().tolist()
        retained.append(c)
    polygons=list(polygon.geoms) if polygon.geom_type=='MultiPolygon' else [polygon]
    positions=[];triangles=[]
    # Densify triangles with boundary samples every 5 m to resolve a sloping channel.
    for poly in polygons:
        rings=[poly.exterior]+list(poly.interiors);verts=[];ends=[]
        for ring in rings:
            coords=list(ring.coords)
            for a,b in zip(coords[:-1],coords[1:]):
                a=np.asarray(a);b=np.asarray(b);n=max(1,int(np.ceil(np.linalg.norm(b-a)/5)))
                verts.extend(a+(b-a)*t/n for t in range(n))
            ends.append(len(verts))
        verts=np.asarray(verts,dtype='float64');faces=mapbox_earcut.triangulate_float64(verts,np.array(ends,dtype='uint32')).reshape(-1,3)
        coords=[(verts[:,1]+half)/spacing,(verts[:,0]+half)/spacing]
        levels=map_coordinates(surface,coords,order=1,mode='nearest')-base
        offset=len(positions);positions.extend(np.c_[verts[:,0],levels,verts[:,1]].tolist());triangles.extend((faces+offset).tolist())
    # Split long water triangles before sampling the sloped surface. A single large
    # triangle otherwise interpolates across several river bends as a visible facet.
    points=[np.asarray(p[:1]+p[2:]) for p in positions]
    pending=[list(t) for t in triangles];refined=[];midpoints={}
    while pending:
        face=pending.pop();lengths=[np.linalg.norm(points[face[i]]-points[face[(i+1)%3]]) for i in range(3)]
        edge=int(np.argmax(lengths))
        if lengths[edge]<=25:
            refined.append(face);continue
        a,b,c=face[edge],face[(edge+1)%3],face[(edge+2)%3];key=tuple(sorted([a,b]))
        if key not in midpoints:
            midpoints[key]=len(points);points.append((points[a]+points[b])/2)
        mid=midpoints[key];pending.extend([[a,mid,c],[mid,b,c]])
    points=np.asarray(points);levels=map_coordinates(surface,[(points[:,1]+half)/spacing,(points[:,0]+half)/spacing],order=1,mode='nearest')-base
    positions=np.c_[points[:,0],levels,points[:,1]].tolist();triangles=refined
    np.savez_compressed(package/'source/sculpted.npz',**fields)
    np.savez_compressed(package/'source/water-mesh.npz',positions=np.asarray(positions),triangles=np.asarray(triangles))
    (package/'source/clasts.json').write_text(json.dumps(retained))
    m['water'].update(half_width_m=half_width_m,mesh_source='source/water-mesh.npz')
    m['artistic_departures'].append({'kind':'channel-width','half_width_m':half_width_m,'reason':'pale silty channel composition'})
    m['cameras']['close'].update(target=[80,170,300],distance=1100,pitch_deg=38)
    m['cameras']['elevated'].update(target=[0,180,0],distance=2600,pitch_deg=52)
    (package/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    print(f'Integrated {len(positions)} water boundary vertices; {len(retained)} bank-safe clast instances')


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--package',default='data/style-patch');args=p.parse_args();integrate_shore(args.package)
