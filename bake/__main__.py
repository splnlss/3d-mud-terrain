"""One command from public DEM to static browser assets: npm run bake."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from importlib.metadata import version
import rasterio

from bake.dem import fetch_patch
from bake.tile import bake_tile
from bake.pyramid import bake_pyramid
from bake.shape import shape_dem
from bake.material import material_fields, SUN_DIRECTION
from bake.imagery import fetch_imagery, fetch_hydrography
from bake.water import prepare_water
from bake.output import output_stage
from bake.tooling import preflight_tools,ROOT
from scipy.ndimage import gaussian_filter
from rasterio.warp import transform
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, default=12000, help='square side in metres')
    parser.add_argument('--spacing', type=int, default=10, help='sample spacing in metres')
    parser.add_argument('--error', type=float, default=None, help='TIN max error in metres (1 for patch, 7.5 for full extent)')
    parser.add_argument('--output', type=Path, default=Path('public/terrain'))
    parser.add_argument('--full', action='store_true', help='70-mile square, 5 LODs')
    parser.add_argument('--style', action='store_true', help='bake rounded, remapped relief')
    parser.add_argument('--gain', type=float, default=5)
    parser.add_argument('--knee', type=float, default=800)
    parser.add_argument('--clods', type=float, default=60, help='clod amplitude in metres')
    parser.add_argument('--edge-width', type=float, default=5500, help='outer relief falloff width in metres')
    parser.add_argument('--rounding', type=float, default=60, help='ridge rounding radius in source metres')
    parser.add_argument('--material', action='store_true', help='bake KTX2 masks and authored detail')
    parser.add_argument('--imagery', action='store_true', help='bake muted satellite field tones')
    parser.add_argument('--water', action='store_true', help='bake NHD + NDWI water geometry')
    parser.add_argument('--compress', action='store_true', help='meshopt + quantization before publishing output')
    args = parser.parse_args()
    if args.full:
        args.size = 112640
    if args.error is None:
        args.error = 7.5 if args.full else 1
    if args.spacing<=0 or args.size<=0 or args.size%args.spacing or args.error<=0:
        parser.error('positive size/spacing/error required; size must be divisible by spacing')
    if args.gain<=0 or args.knee<=0 or args.rounding<0 or args.edge_width<0:
        parser.error('gain/knee must be positive; rounding/edge width must be nonnegative')
    if args.material and (not args.full or not args.style):
        parser.error('--material requires --full --style')
    if args.imagery or args.water:
        if not args.full or not args.style or not args.material:
            parser.error('--imagery / --water require --full --style --material')
        if args.spacing>40 or 40%args.spacing:
            parser.error('imagery and water require sample spacing that divides 40 metres')
    if args.full and (args.size//args.spacing)%16:
        parser.error('full extent grid segments must be divisible by 16')
    tool_versions,compress_command=preflight_tools(args.material,args.compress)
    print(f'Reading {args.size} m San Luis DEM at {args.spacing} m spacing…', flush=True)
    heights, manifest = fetch_patch(args.size, args.spacing)
    base = float(heights.min())
    factor = max(1,40//args.spacing)
    source_coarse = heights[::factor,::factor].copy() if args.material else None
    if args.style:
        print('Shaping rounded relief…', flush=True)
        edge = min(args.edge_width, args.size*.15)
        heights = shape_dem(heights, args.size, base, args.gain, args.knee, args.clods, edge,
                            rounding_sigma=args.rounding/args.spacing)
        manifest['style'] = {'gain': args.gain, 'knee_m': args.knee, 'clod_amplitude_m': args.clods}
        manifest['style']['edge_width_m'] = edge
        manifest['style']['rounding_m'] = args.rounding
    fields = None
    water = None
    if args.imagery or args.water:
        imagery, provenance = fetch_imagery(manifest)
        manifest['imagery'] = provenance
        if args.water:
            print('Preparing mapped water…', flush=True)
            water = prepare_water(heights, manifest, imagery, fetch_hydrography(manifest), base,
                                   source_coarse=source_coarse)
            manifest['water'] = water['metadata']
    if args.material:
        macro=shape_dem(source_coarse,args.size,base,args.gain,args.knee,0,edge,
                         rounding_sigma=args.rounding/(args.spacing*factor))
        fields = material_fields(heights[::factor, ::factor], args.spacing*factor,landform=macro)
        manifest['material'] = {'mask_size': 256, 'detail_size': 512,
                                'detail_authoring': 'periodic packed gravel and smooth crust; seed 4271',
                                'channels': ['crust', 'tone', 'dust', 'shore_distance' if water else 'AO']}
        if args.imagery:
            # Blur removes narrow photographic road/building cues; NDVI keeps fields as tone.
            valid=imagery['scl']>0
            weight=gaussian_filter(valid.astype('float32'),2)
            tone=gaussian_filter(np.clip(imagery['ndvi'],0,1)*valid,2)/np.maximum(weight,1e-6)
            tone[weight<.01]=.3
            fields[:, :, 1] = np.clip(.5+(tone-.3)*.32, .35, .65)
    with output_stage(args.output) as output:
        if args.full:
            stats = bake_pyramid(heights, args.size, base, output, max_error=args.error,
                                 fields=fields, water=water)
        else:
            stats = bake_tile(heights, manifest['local_sample_bounds_m'], base, output,
                              max_error=args.error)
        manifest.update({'base_elevation_m': base, 'mesh': stats,
                         'slice': '07' if args.imagery else '05' if args.water else '04' if args.material else '03' if args.style else '02' if args.full else '01'})
        indices = np.linspace(0,len(heights)-1,129).round().astype('int32')
        manifest['preview_heights_m'] = (heights[np.ix_(indices,indices)]-base).round(1).tolist()
        manifest['lighting'] = {'sun_direction': list(SUN_DIRECTION), 'realtime_shadows': False}
        manifest['toolchain'] = {'python': sys.version.split()[0], 'numpy': np.__version__,
            'rasterio': rasterio.__version__, 'gdal': rasterio.__gdal_version__,
            'pydelatin': version('pydelatin'), **tool_versions}
        views = {'Culebra range': (-105.1856,37.1223,16000),
                 'Rio Grande gorge': (-105.74,37.15,12000),
                 'Sanchez Reservoir': (-105.41442,37.09332,6500),
                 'Valley fields': (-105.80,37.44,12000)}
        manifest['views'] = {}
        for name, (lon, lat, distance) in views.items():
            x, y = transform('EPSG:4326', manifest['crs'], [lon], [lat])
            manifest['views'][name] = {'x': x[0]-manifest['center_utm_m'][0],
                                      'z': manifest['center_utm_m'][1]-y[0], 'distance': distance}
        (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
        if args.compress:
            subprocess.run([*compress_command,str(output.resolve())],check=True,cwd=ROOT)
    print(f"Baked {stats['triangles']:,} triangles → {args.output}/tileset.json", flush=True)


if __name__ == '__main__':
    main()
