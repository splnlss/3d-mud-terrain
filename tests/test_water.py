"""Water triangulation must preserve islands and identical levels across tiles."""
import numpy as np
from shapely.geometry import Polygon

from bake.water import water_mesh, lower_water_bed
from bake.water import prepare_water, lake_surface_height


def test_flat_lake_preserves_island_and_tile_boundary_levels():
    polygon = Polygon([(-40,-40),(40,-40),(40,40),(-40,40)],
                      [[(-10,-10),(-10,10),(10,10),(10,-10)]])
    surface = np.full((9,9), 20, dtype='float32')
    pos, faces = water_mesh([polygon], surface, (-40,-40,40,40), 80)
    triangles = pos[faces]
    area = np.abs(np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])[:,1]).sum()/2
    assert area == 6000  # 80² minus a 20² island.
    assert (pos[:,1] == 20).all()
    for bounds in [(-40,-40,0,40), (0,-40,40,40)]:
        cropped, _ = water_mesh([polygon], surface, bounds, 80)
        assert (cropped[cropped[:,0]==0,1] == 20).all()


def test_dry_tile_emits_no_water_geometry():
    surface = np.zeros((3,3), dtype='float32')
    pos, faces = water_mesh([], surface, (-10,-10,10,10), 20)
    assert pos.shape == (0,3) and faces.shape == (0,3)


def test_lod_bed_clearance_cannot_lower_unmapped_dry_land():
    patch = np.full((3,3), 100, dtype='float32')
    mask = np.zeros((3,3), dtype='uint8')
    mask[1,1] = 1
    water = {'surface': np.full((3,3), 120, dtype='float32'),
             'ground': patch.copy(), 'mask': mask}
    result = lower_water_bed(patch, (-10,-10,10,10), 20, 0, 20, water)
    assert result[1,1] == 86
    assert (result[mask==0] == 100).all()
    assert (patch==100).all()


def test_land_clod_displacement_does_not_make_lake_water_lumpy():
    from rasterio.warp import transform_geom
    from shapely.geometry import box, mapping, LineString
    cx, cy = 462728, 4117142
    lake = transform_geom('EPSG:32613','EPSG:4326', mapping(box(cx-100,cy-100,cx+100,cy+100)))
    stream = transform_geom('EPSG:32613','EPSG:4326', mapping(LineString([(cx-200,cy),(cx+200,cy)])))
    hydro = {'service':'test fixture', 'layers': {
        '6':[{'geometry':stream,'properties':{'ftype':460}}],
        '12':[{'geometry':lake,'properties':{'ftype':390}}]}}
    manifest = {'size_m':400,'spacing_m':10,'center_utm_m':[cx,cy],
                'style':{'gain':1,'knee_m':1000000,'edge_width_m':0}}
    imagery = {'ndwi':np.full((11,11),-1),'scl':np.full((11,11),4)}
    raw = np.full((11,11),2100,dtype='float32')
    levels = []
    for offset in [-20,20]:
        sculpted = np.full((41,41),2100+offset,dtype='float32')
        water = prepare_water(sculpted, manifest, imagery, hydro, 2000, source_coarse=raw)
        levels.append(water['surface'][5,5])
    assert abs(levels[0]-levels[1]) < .001


def test_mapped_lake_depression_fills_to_the_lowest_adjacent_bank():
    heights = np.full((5,5),120,dtype='float32')
    heights[1:4,1:4] = 100
    heights[0,2] = 110  # Lowest outlet in the mapped bank.
    inside = np.zeros((5,5),dtype=bool)
    inside[1:4,1:4] = True
    assert lake_surface_height(heights,inside)==110


def test_shore_intersections_match_when_adjacent_tiles_have_different_lods():
    from shapely.geometry import LineString
    x = np.linspace(-100,100,101)
    polygon = LineString(np.column_stack([x,30*np.sin((x+21)/23)+6*np.sin(x/11)])).buffer(10)
    surface = np.full((21,21),20,dtype='float32')
    left, _ = water_mesh([polygon],surface,(-200,-100,0,100),400)
    right, _ = water_mesh([polygon],surface,(0,0,100,100),400)
    a = np.sort(left[np.isclose(left[:,0],0),2])
    b = np.sort(right[np.isclose(right[:,0],0),2])
    np.testing.assert_allclose(a,b,atol=.001)


def water_fixture(size=400):
    from rasterio.warp import transform_geom
    from shapely.geometry import mapping, LineString
    cx,cy=462728,4117142
    stream=transform_geom('EPSG:32613','EPSG:4326',mapping(LineString([(cx-size/2,cy),(cx+size/2,cy)])))
    manifest={'size_m':size,'spacing_m':10,'center_utm_m':[cx,cy],
              'style':{'gain':1,'knee_m':1000000000,'edge_width_m':0}}
    n=size//40+1
    imagery={'ndwi':np.full((n,n),-1),'scl':np.full((n,n),4)}
    hydro={'service':'test fixture','layers':{'6':[{'geometry':stream,'properties':{'ftype':460}}],'12':[]}}
    return manifest,imagery,hydro


def test_negative_clods_cannot_leave_a_dry_bank_below_water():
    manifest,imagery,hydro=water_fixture()
    raw=np.full((11,11),2100,dtype='float32')
    heights=np.full((41,41),2040,dtype='float32')
    water=prepare_water(heights,manifest,imagery,hydro,2000,source_coarse=raw)
    # 100 m north of the centreline, 55 m beyond the widened shoreline.
    assert heights[10,20]>=water['surface'][2,5]+2000


def test_only_named_main_canals_survive_and_drain_names_cannot_widen_as_rivers():
    from bake.water import channel_half_width
    assert channel_half_width({'ftype':336,'gnis_name':'Acequia Madre'})==10
    assert channel_half_width({'ftype':336,'gnis_name':'Unnamed Lateral'})==0
    assert channel_half_width({'ftype':336,'gnis_name':'Rio Grande Drain'})==0
    assert channel_half_width({'ftype':336})==0
    assert channel_half_width({'ftype':460,'gnis_name':'Rio Grande'})==180
    assert channel_half_width({'ftype':460,'gnis_name':'Rio Grande Drain'})<180


def test_lod_clearance_checks_native_polygon_membership_not_a_wide_coarse_mask():
    patch=np.full((3,3),100,dtype='float32')
    native=np.zeros((9,9),dtype='uint8');native[4,4]=1
    water={'surface':np.full((3,3),120,dtype='float32'),'ground':patch.copy(),
           'mask':np.ones((3,3),dtype='uint8'),'native_mask':native}
    result=lower_water_bed(patch,(-10,-10,10,10),20,0,20,water)
    assert result[1,1]<100
    assert result[0,0]==100 and result[1,0]==100


def test_main_river_profile_wins_over_a_steep_tributary_inside_its_width():
    from shapely.geometry import LineString,mapping
    from rasterio.warp import transform_geom
    manifest,imagery,hydro=water_fixture(800)
    cx,cy=manifest['center_utm_m']
    hydro['layers']['6'][0]['properties']['gnis_name']='Rio Grande'
    tributary=transform_geom('EPSG:32613','EPSG:4326',mapping(LineString([(cx,cy),(cx,cy+400)])))
    hydro['layers']['6'].append({'geometry':tributary,'properties':{'ftype':460}})
    north=np.linspace(400,-400,21)[:,None]
    raw=np.repeat(2100+np.maximum(north,0),21,axis=1).astype('float32')
    heights=np.repeat(np.repeat(raw,4,axis=0),4,axis=1)[:81,:81].copy()
    water=prepare_water(heights,manifest,imagery,hydro,2000,source_coarse=raw)
    assert abs(water['surface'][6,10]-water['surface'][10,6])<2


def test_thirty_metre_wide_lake_keeps_one_plane_including_its_vector_shore():
    from shapely.geometry import box,mapping
    from rasterio.warp import transform_geom
    manifest,imagery,hydro=water_fixture(800)
    cx,cy=manifest['center_utm_m']
    lake=transform_geom('EPSG:32613','EPSG:4326',mapping(box(cx-250,cy+185,cx+250,cy+215)))
    hydro['layers']['12']=[{'geometry':lake,'properties':{'ftype':390}}]
    raw=np.repeat(np.linspace(2120,2080,21)[None,:],21,axis=0).astype('float32')
    heights=np.full((81,81),2100,dtype='float32')
    water=prepare_water(heights,manifest,imagery,hydro,2000,source_coarse=raw)
    lake_polygon=next(p for p in water['polygons'].geometries if p.centroid.y>100)
    positions,_=water_mesh([lake_polygon],water['surface'],(-400,-400,400,400),800)
    assert np.ptp(positions[:,1])<.001
