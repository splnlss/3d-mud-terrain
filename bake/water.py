"""Mapped water geometry and baked shoreline attributes."""
import re
import mapbox_earcut
import numpy as np
from rasterio.features import rasterize, shapes
from rasterio.transform import from_origin
from rasterio.warp import transform_geom
from scipy.ndimage import binary_dilation, distance_transform_edt, find_objects, gaussian_filter, label, map_coordinates
from shapely import STRtree, union_all
from shapely.affinity import translate
from shapely.geometry import Polygon, box, mapping, shape

from bake.dem import CRS
from bake.shape import remap_height


def lake_surface_height(heights, inside):
    if not inside.any():
        raise ValueError('lake mask is empty')
    bank = binary_dilation(inside) & ~inside
    existing = float(np.median(heights[inside]))
    return max(existing, float(heights[bank].min())) if bank.any() else existing


def lower_water_bed(patch, bounds, size, base, error, water):
    xx = np.linspace(bounds[0], bounds[2], patch.shape[1])[None,:]
    zz = -np.linspace(bounds[3], bounds[1], patch.shape[0])[:,None]
    row, col = np.broadcast_arrays((.5+zz/size)*(water['surface'].shape[0]-1),
                                   (.5+xx/size)*(water['surface'].shape[1]-1))
    level = map_coordinates(water['surface'], [row,col], order=1, mode='nearest')+base
    ground = map_coordinates(water['ground'], [row,col], order=1, mode='nearest')+base
    membership = water.get('native_mask',water['mask'])
    native_row=(.5+zz/size)*(membership.shape[0]-1)
    native_col=(.5+xx/size)*(membership.shape[1]-1)
    native_row,native_col=np.broadcast_arrays(native_row,native_col)
    mapped = map_coordinates(membership.astype('uint8'), [native_row,native_col], order=0, mode='nearest')>0
    wet = mapped & ((level-ground)>10)
    result = patch.copy()
    result[wet] = np.minimum(result[wet], level[wet]-error*1.5-4)
    return result


def water_mesh(polygons, surface, bounds, size):
    clip = box(*bounds)
    if isinstance(polygons, STRtree):
        candidates = [polygons.geometries[i] for i in polygons.query(clip)]
    else:
        candidates = polygons
    positions, triangles = [], []
    count = 0
    for polygon in candidates:
        # One canonical shoreline at every LOD prevents gaps at shared tile edges.
        polygon = polygon.intersection(clip)
        parts = list(polygon.geoms) if hasattr(polygon, 'geoms') else [polygon]
        for part in parts:
            if not isinstance(part, Polygon) or part.is_empty or part.area < 1:
                continue
            rings = [np.array(part.exterior.coords)[:-1]]
            rings.extend(np.array(ring.coords)[:-1] for ring in part.interiors)
            xy = np.concatenate(rings).astype('float64')
            ends = np.cumsum([len(ring) for ring in rings]).astype('uint32')
            indices = mapbox_earcut.triangulate_float64(xy, ends).reshape(-1, 3)
            row = (.5-xy[:, 1]/size)*(surface.shape[0]-1)
            col = (.5+xy[:, 0]/size)*(surface.shape[1]-1)
            level = map_coordinates(surface, [row, col], order=1, mode='nearest')
            pos = np.column_stack([xy[:, 0], level, -xy[:, 1]]).astype('float32')
            # Earcut's winding is not guaranteed after polygon clipping. Enforce Y-up.
            t = pos[indices]
            flip = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0])[:,1] < 0
            indices[flip] = indices[flip][:, [0,2,1]]
            positions.append(pos)
            triangles.append(indices+count)
            count += len(pos)
    if not positions:
        return np.empty((0,3), dtype='float32'), np.empty((0,3), dtype='uint32')
    return np.concatenate(positions), np.concatenate(triangles)


def channel_half_width(properties):
    name=(properties.get('gnis_name') or '').strip().casefold()
    kind=properties.get('ftype')
    if kind==336:
        if not name or re.search(r'\b(drain|lateral)s?\b',name):
            return 0
        return 10
    if name=='rio grande' and kind in [460,558]:
        return 180
    return 75 if name=='culebra creek' else 45


def channel_surface(source, channels, size, spacing):
    """Nearest centreline within each reach; wider rivers own confluence overlaps."""
    result=source.copy()
    count=len(source)
    half=size/2
    for geometry,width in sorted(channels,key=lambda item:item[1]):
        # Carry the reach profile beyond its shore to support bilinear edge samples.
        footprint=geometry.buffer(width+2*spacing,quad_segs=8)
        west,south,east,north=footprint.bounds
        c0=max(0,int(np.floor((west+half)/spacing))-1)
        c1=min(count,int(np.ceil((east+half)/spacing))+2)
        r0=max(0,int(np.floor((half-north)/spacing))-1)
        r1=min(count,int(np.ceil((half-south)/spacing))+2)
        if c1<=c0 or r1<=r0:
            continue
        transform=from_origin(-half+c0*spacing-spacing/2,half-r0*spacing+spacing/2,spacing,spacing)
        shape2=(r1-r0,c1-c0)
        core=rasterize([(mapping(geometry),1)],out_shape=shape2,transform=transform,
                        all_touched=True,dtype='uint8')>0
        if not core.any():
            continue
        inside=rasterize([(mapping(footprint),1)],out_shape=shape2,transform=transform,
                          all_touched=True,dtype='uint8')>0
        _,nearest=distance_transform_edt(~core,return_indices=True)
        values=source[r0:r1,c0:c1][nearest[0],nearest[1]]
        result[r0:r1,c0:c1][inside]=values[inside]
    return result


def prepare_water(heights, manifest, imagery, hydrography, base, source_coarse):
    """Mutate sculpted heights to recess mapped water and support its dry banks."""
    size=manifest['size_m']
    spacing=40
    factor=40//manifest['spacing_m']
    count=len(source_coarse)
    cx,cy=manifest['center_utm_m']
    grid=from_origin(-size/2-spacing/2,size/2+spacing/2,spacing,spacing)
    channels,wide_shapes,lake_polygons,vector_water=[],[],[],[]
    names=set()
    omitted_canals=0
    for layer,features in hydrography['layers'].items():
        for feature in features:
            if not feature.get('geometry'):
                continue
            polygon=translate(shape(transform_geom('EPSG:4326',CRS,feature['geometry'])),-cx,-cy)
            properties=feature['properties']
            name=properties.get('gnis_name') or ''
            if layer=='6':
                width=channel_half_width(properties)
                if width==0:
                    omitted_canals+=1
                    continue
                channels.append((polygon,width))
                buffered=polygon.buffer(width,quad_segs=8)
                wide_shapes.append((mapping(buffered),1))
                vector_water.append(buffered)
            elif polygon.area>10000:
                buffered=polygon.buffer(20,quad_segs=8)
                lake_polygons.append(buffered)
                vector_water.append(buffered)
            else:
                continue
            if name:
                names.add(name)
    if not channels:
        raise ValueError('NHD contains no mapped channels for this extent')
    wide=rasterize(wide_shapes,out_shape=(count,count),transform=grid,
                   all_touched=True,dtype='uint8')>0
    # Connected mapped lake outlines share one plane, including narrow water bodies.
    merged_lakes=union_all(lake_polygons)
    lake_parts=list(merged_lakes.geoms) if hasattr(merged_lakes,'geoms') else [merged_lakes]
    lake_shapes=[(mapping(polygon),i+1) for i,polygon in enumerate(lake_parts) if not polygon.is_empty]
    lakes=rasterize(lake_shapes,out_shape=(count,count),transform=grid,all_touched=True,
                    dtype='int32') if lake_shapes else np.zeros((count,count),dtype='int32')
    detected=(imagery['ndwi']>.2)&(imagery['scl']==6)
    wet=wide|(lakes>0)|detected
    style=manifest['style']
    center_surface=remap_height(gaussian_filter(source_coarse,style.get('rounding_m',60)/spacing),
                                base,style['gain'],style['knee_m'])-base
    edge_width=style.get('edge_width_m',0)
    if edge_width>0:
        axis=np.linspace(-size/2,size/2,count)
        edge=np.minimum(size/2-np.abs(axis[:,None]),size/2-np.abs(axis[None,:]))
        t=np.clip(edge/edge_width,0,1)
        center_surface*=t*t*(3-2*t)
    surface=channel_surface(center_surface,channels,size,spacing)

    def fill_bodies(labels):
        for body_id,region in enumerate(find_objects(labels),start=1):
            if region is None:
                continue
            rows=slice(max(0,region[0].start-1),min(count,region[0].stop+1))
            cols=slice(max(0,region[1].start-1),min(count,region[1].stop+1))
            inside=labels[rows,cols]==body_id
            surface[rows,cols][inside]=lake_surface_height(center_surface[rows,cols],inside)+.5
        if (labels>0).any():
            distance,nearest=distance_transform_edt(labels==0,return_indices=True)
            margin=(distance<=2)&(labels==0)
            surface[margin]=surface[nearest[0][margin],nearest[1][margin]]

    fill_bodies(lakes)
    isolated=detected&~wide&(lakes==0)
    isolated_labels,pond_count=label(isolated)
    fill_bodies(isolated_labels)
    detected_polygons=[]
    for geo,value in shapes(isolated.astype('uint8'),mask=isolated,transform=grid):
        if value:
            detected_polygons.append(shape(geo).buffer(20).buffer(-10))
    merged=union_all(vector_water+detected_polygons,grid_size=1)
    polygons=list(merged.geoms) if hasattr(merged,'geoms') else [merged]
    polygons=[polygon.simplify(5,preserve_topology=True) for polygon in polygons
              if not polygon.is_empty and polygon.area>2000]
    native_spacing=size/(len(heights)-1)
    native_grid=from_origin(-size/2-native_spacing/2,size/2+native_spacing/2,
                            native_spacing,native_spacing)
    # Point-centre membership must match the samples lowered by every terrain LOD.
    native_wet=rasterize([(mapping(polygon),1) for polygon in polygons],out_shape=heights.shape,
                         transform=native_grid,all_touched=False,dtype='uint8')>0
    distance=distance_transform_edt(~wet)*spacing
    band=np.exp(-distance/90).astype('float32')
    for row0 in range(0,len(heights),128):
        row1=min(len(heights),row0+128)
        rows,cols=np.meshgrid(np.arange(row0,row1)/factor,np.arange(heights.shape[1])/factor,indexing='ij')
        mask=native_wet[row0:row1]
        level=map_coordinates(surface,[rows,cols],order=1,mode='nearest')+base
        macro=map_coordinates(center_surface,[rows,cols],order=1,mode='nearest')+base
        damp=map_coordinates(band,[rows,cols],order=1,mode='nearest')
        shore=map_coordinates(distance,[rows,cols],order=1,mode='nearest')
        chunk=heights[row0:row1]
        chunk*=1-damp
        chunk+=macro*damp
        # Preserve a dry bank above the plane. The outer blend avoids a new step;
        # the coarse mask's conservative halo covers native shores within 100 m.
        t=np.clip((shore-140)/140,0,1)
        support=1-t*t*(3-2*t)
        dry=~mask
        chunk[dry]+=np.maximum(level[dry]+2-chunk[dry],0)*support[dry]
        chunk[mask]=np.minimum(chunk[mask],level[mask]-20)
    ground=heights[::factor,::factor]-base
    shore_distance=np.clip(distance_transform_edt(wet)*spacing/120,0,1).astype('float32')
    return {'polygons':STRtree(polygons),'surface':surface,'ground':ground,'band':band,
            'shore_distance':shore_distance,'mask':wet,'native_mask':native_wet,
            'metadata':{'service':hydrography['service'],'sources':hydrography.get('sources',[]),
              'named_features':sorted(names),'ndwi_threshold':.2,
              'widths_m':{'Rio Grande':360,'Culebra':150,'canal':20,'other':90},
              'canal_filter':'named main canals/acequias; omit drains, laterals and unnamed ditches',
              'omitted_canals':omitted_canals,'mapped_channel_count':len(channels),
              'lake_count':len(lake_shapes),'wet_fraction':float(wet.mean()),'detected_pond_count':pond_count,
              'bank_clearance_m':2,'bank_clod_damping_m':140,
              'lake_levels':'connected mapped outlines, all-touched depression fill, constant plane',
              'river_levels':'own-reach source DEM profile; wider river owns confluence overlaps'}}
