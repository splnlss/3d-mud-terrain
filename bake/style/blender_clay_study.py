"""Render the continuous clay calibration specimen (Blender Python)."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--scan',type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);root=args.study.resolve()
    data=np.load(root/'surface.npz');height=data['height'].copy();n,m=height.shape
    if args.scan:height-=data['aggregate_height']
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    x,y=np.meshgrid(np.linspace(-.6,.6,m),np.linspace(.6,-.6,n))
    # Image row zero is north, matching the standard material package convention.
    positions=np.stack([x,y,height],axis=-1).astype('float32')
    indices=np.arange(n*m,dtype='int32').reshape(n,m)
    faces=np.stack([indices[:-1,:-1],indices[1:,:-1],indices[1:,1:],indices[:-1,1:]],axis=-1).reshape(-1,4)
    mesh=bpy.data.meshes.new('Continuous clay and embedded crust')
    mesh.vertices.add(n*m);mesh.vertices.foreach_set('co',positions.ravel())
    mesh.loops.add(faces.size);mesh.loops.foreach_set('vertex_index',faces.ravel())
    mesh.polygons.add(len(faces));mesh.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype='int32'))
    mesh.polygons.foreach_set('loop_total',np.full(len(faces),4,dtype='int32'))
    mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool));mesh.update()
    obj=bpy.data.objects.new('Single cohesive clay surface',mesh);bpy.context.collection.objects.link(obj)
    colour=mesh.color_attributes.new(name='Intrinsic clay colour',type='FLOAT_COLOR',domain='POINT')
    rgba=np.concatenate([data['base_color'],np.ones((n,m,1))],axis=-1).astype('float32')
    colour.data.foreach_set('color',rgba.ravel())
    finish=mesh.attributes.new(name='Physical finish',type='FLOAT',domain='POINT')
    finish.data.foreach_set('value',data['roughness'].ravel())
    material=bpy.data.materials.new('Clay, dust and fused crust');material.use_nodes=True
    nodes=material.node_tree.nodes;links=material.node_tree.links;bsdf=nodes.get('Principled BSDF')
    bsdf.inputs['IOR'].default_value=1.47;bsdf.inputs['Specular IOR Level'].default_value=.5
    attr=nodes.new('ShaderNodeAttribute');attr.attribute_name=colour.name
    links.new(attr.outputs['Color'],bsdf.inputs['Base Color'])
    rough=nodes.new('ShaderNodeAttribute');rough.attribute_name=finish.name
    links.new(rough.outputs['Fac'],bsdf.inputs['Roughness'])
    geometry=nodes.new('ShaderNodeNewGeometry');pore=nodes.new('ShaderNodeTexNoise')
    pore.inputs['Scale'].default_value=3000;pore.inputs['Detail'].default_value=2
    links.new(geometry.outputs['Position'],pore.inputs['Vector'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.000035
    links.new(pore.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    if args.scan:
        # Registered scan channels supply fine material detail; the procedural
        # hemisphere clods are removed from geometry above for this comparison.
        scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs['Scale'].default_value=10
        links.new(geometry.outputs['Position'],scale.inputs[0])
        def scan(name,colour=False):
            node=nodes.new('ShaderNodeTexImage')
            node.image=bpy.data.images.load(str((args.scan/f'{name}.png').resolve()),check_existing=True)
            node.image.colorspace_settings.name='sRGB' if colour else 'Non-Color'
            node.projection='BOX';node.projection_blend=.3;node.extension='REPEAT'
            links.new(scale.outputs['Vector'],node.inputs['Vector']);return node
        base=scan('base-color',True)
        tint=nodes.new('ShaderNodeHueSaturation');tint.inputs['Saturation'].default_value=.65
        tint.inputs['Value'].default_value=1.55
        links.new(base.outputs['Color'],tint.inputs['Color']);links.new(tint.outputs[0],bsdf.inputs['Base Color'])
        finish_scan=scan('roughness');finish_range=nodes.new('ShaderNodeMapRange')
        finish_range.inputs['To Min'].default_value=.45;finish_range.inputs['To Max'].default_value=.85
        links.new(finish_scan.outputs['Color'],finish_range.inputs['Value']);links.new(finish_range.outputs['Result'],bsdf.inputs['Roughness'])
        depth=scan('height');relief=nodes.new('ShaderNodeBump')
        relief.inputs['Strength'].default_value=.8;relief.inputs['Distance'].default_value=.003
        links.new(depth.outputs['Color'],relief.inputs['Height']);links.new(relief.outputs['Normal'],bsdf.inputs['Normal'])
    obj.data.materials.append(material)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.001))
    ground=bpy.context.object;groundmat=bpy.data.materials.new('Distant clay');groundmat.diffuse_color=(.235,.205,.165,1)
    ground.data.materials.append(groundmat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=128;scene.cycles.use_denoising=True
    scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.72,.76,.82,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
    bpy.ops.object.light_add(type='SUN',location=(-.9,.8,.42));sun=bpy.context.object
    sun.data.energy=3;sun.data.angle=math.radians(6);sun.data.color=(1,.88,.72);aim(sun,(0,0,0))
    bpy.ops.object.camera_add(location=(.40,-.72,.36));camera=bpy.context.object;scene.camera=camera
    target=(0,.025,.07);aim(camera,target);camera.data.lens=58;camera.data.clip_start=.005;camera.data.clip_end=300
    bpy.ops.object.empty_add(location=target);focus=bpy.context.object;focus.name='Material focal plane'
    camera.data.dof.use_dof=True;camera.data.dof.focus_object=focus;camera.data.dof.aperture_fstop=11
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.65
    tag='scan-study' if args.scan else 'clay-study'
    scene.render.filepath=str(root/f'{tag}.png');bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(root/f'{tag}.blend'))
    (root/f'{tag}-settings.json').write_text(json.dumps({'camera_location':list(camera.location),
        'target':target,'lens_mm':58,'fstop':11,'scan':str(args.scan) if args.scan else None,'exposure':.65,'world_strength':.4,
        'sun_energy':3,'sun_angle_deg':6,'single_continuous_mesh':True,
        'note':'Material/shape calibration study; not the San Luis DEM'},indent=2)+'\n')


if __name__=='__main__':main()
