"""Reference-led clay material preview with world-space box projection.

Colour is an AI-authored reference interpretation; relief is separately authored.
The generated colour still contains residual shading and is a draft asset.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_preview import set_camera


def clay_material(name, maps, albedo, shade=1):
    maps = Path(maps).resolve()
    meta = json.loads((maps/'manifest.json').read_text())
    material = bpy.data.materials.new(name);material.use_nodes=True
    nodes = material.node_tree.nodes;links = material.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['IOR'].default_value=1.48
    bsdf.inputs['Specular IOR Level'].default_value=.45
    bsdf.inputs['Coat Weight'].default_value=0
    geometry=nodes.new('ShaderNodeNewGeometry')
    scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE'
    scale.inputs['Scale'].default_value=1/meta['span_m']
    links.new(geometry.outputs['Position'],scale.inputs[0])
    def image(path,colour=False):
        node=nodes.new('ShaderNodeTexImage')
        node.image=bpy.data.images.load(str(Path(path).resolve()),check_existing=True)
        node.image.colorspace_settings.name='sRGB' if colour else 'Non-Color'
        node.projection='BOX';node.projection_blend=.35;node.extension='REPEAT'
        links.new(scale.outputs['Vector'],node.inputs['Vector'])
        return node
    colour=image(albedo,True)
    saturation=nodes.new('ShaderNodeHueSaturation')
    saturation.inputs['Saturation'].default_value=.65 if shade==1 else .25
    links.new(colour.outputs['Color'],saturation.inputs['Color'])
    tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
    tint.inputs[2].default_value=(.65,.65,.63,1) if shade!=1 else (1,1,1,1)
    if shade == 1:
        attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='Style fields'
        separate=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],separate.inputs['Color'])
        palette=nodes.new('ShaderNodeMixRGB')
        palette.inputs[1].default_value=(.9,1.0,1.12,1)
        palette.inputs[2].default_value=(1.16,1.1,.96,1)
        links.new(separate.outputs['Red'],palette.inputs[0]);links.new(palette.outputs[0],tint.inputs[2])
    links.new(saturation.outputs['Color'],tint.inputs[1]);links.new(tint.outputs[0],bsdf.inputs['Base Color'])
    rough=image(maps/'roughness.png')
    dry=nodes.new('ShaderNodeMapRange');dry.inputs['To Min'].default_value=.38;dry.inputs['To Max'].default_value=.78
    links.new(rough.outputs['Color'],dry.inputs['Value'])
    wet=nodes.new('ShaderNodeAttribute');wet.attribute_name='Clay wetness'
    finish=nodes.new('ShaderNodeMixRGB');finish.inputs[2].default_value=(.43,.43,.43,1)
    links.new(wet.outputs['Fac'],finish.inputs[0]);links.new(dry.outputs['Result'],finish.inputs[1])
    links.new(finish.outputs[0],bsdf.inputs['Roughness'])
    height=image(maps/'height.png')
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.8
    if shade == 1:
        relief=nodes.new('ShaderNodeMapRange');relief.inputs['To Min'].default_value=.85;relief.inputs['To Max'].default_value=.18
        links.new(separate.outputs['Red'],relief.inputs['Value']);links.new(relief.outputs['Result'],bump.inputs['Strength'])
    bump.inputs['Distance'].default_value=meta['height_range_m'][1]-meta['height_range_m'][0]
    links.new(height.outputs['Color'],bump.inputs['Height'])
    grain=nodes.new('ShaderNodeTexNoise');grain.inputs['Scale'].default_value=12
    grain.inputs['Detail'].default_value=2;grain.inputs['Roughness'].default_value=.75
    links.new(geometry.outputs['Position'],grain.inputs['Vector'])
    pores=nodes.new('ShaderNodeBump');pores.inputs['Strength'].default_value=.2
    pores.inputs['Distance'].default_value=.006
    links.new(grain.outputs['Fac'],pores.inputs['Height'])
    links.new(bump.outputs['Normal'],pores.inputs['Normal']);links.new(pores.outputs['Normal'],bsdf.inputs['Normal'])
    return material


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--maps',type=Path,required=True);parser.add_argument('--albedo',type=Path,required=True)
    parser.add_argument('--tag',default='material-v6')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);package=args.package.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(package/'source/master.blend'))
    terrain=bpy.data.objects['Terrain']
    fields=np.load(package/'source/sculpted.npz')
    wet=terrain.data.attributes.new(name='Clay wetness',type='FLOAT',domain='POINT')
    wet.data.foreach_set('value',fields['wet_band'].astype('float32').ravel())
    matrix=clay_material('Reference clay matrix',args.maps,args.albedo)
    aggregate=clay_material('Reference fused crust',args.maps,args.albedo,.72)
    terrain.data.materials.clear();terrain.data.materials.append(matrix)
    meshes=set()
    for obj in bpy.data.objects:
        if obj.type!='MESH' or obj==terrain or obj.get('style_role')=='water':continue
        if obj.data.name in meshes:continue
        meshes.add(obj.data.name);obj.data.materials.clear();obj.data.materials.append(aggregate)
    # Pale opaque silt remains water, with a muted taupe value and glancing sheen.
    for obj in bpy.data.objects:
        if obj.type=='MESH' and obj.get('style_role')=='water':
            water=obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
            water.inputs['Base Color'].default_value=(.66,.62,.52,1)
            for polygon in obj.data.polygons:polygon.use_smooth=True
            water.inputs['Roughness'].default_value=.48
            # The stylised channel shades as a level surface. DEM-supported
            # triangles must not turn its specular into a faceted ribbon.
            flat=obj.data.materials[0].node_tree.nodes.new('ShaderNodeCombineXYZ')
            flat.inputs['Z'].default_value=1
            obj.data.materials[0].node_tree.links.new(flat.outputs[0],water.inputs['Normal'])
    manifest=json.loads((package/'manifest.json').read_text())
    scene=bpy.context.scene;scene.view_settings.exposure=.55;scene.cycles.samples=64
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
    # Camera/light stay fixed for the comparison; exposure is recorded explicitly.
    set_camera(manifest,'close')
    scene.render.filepath=str(package/f'review/{args.tag}-close.png');bpy.ops.render.render(write_still=True)
    pose=manifest['cameras']['close'];pose['distance']=480;pose['pitch_deg']=36
    set_camera(manifest,'close')
    scene.render.filepath=str(package/f'review/{args.tag}-detail.png');bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(package/f'source/{args.tag}.blend'))
    (package/f'review/{args.tag}-settings.json').write_text(json.dumps({'projection':'world-space box blend .35',
        'repeat_m':32,'exposure':.55,'ambient_strength':.45,'shore_roughness':.43,'ior':1.48,'specular_ior_level':.45,'coat_weight':0,
        'matrix_saturation':.65,'crust_saturation':.25,'water_colour_linear':[.66,.62,.52],'water_roughness':.48,'water_normal_world':[0,0,1],
        'dry_roughness_remap':[.38,.78],'exposed_clay_bump_strength':.18,'crust_bump_strength':.85,
        'geometry':'unchanged source master','albedo':str(args.albedo),'maps':str(args.maps),
        'caveat':'AI colour texture contains residual shading; independent authored relief'},indent=2)+'\n')


if __name__=='__main__':main()
