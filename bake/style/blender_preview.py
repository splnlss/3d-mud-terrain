"""Blender source-scene preview. Run with Blender's Python, not the bake venv."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector,Quaternion,Matrix
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clast_mesh import make_clast_mesh


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def terrain_geometry(heights,size,base):
    n,m=heights.shape
    vertices=[(-size/2+col*size/(m-1),size/2-row*size/(n-1),float(heights[row,col]-base))
              for row in range(n) for col in range(m)]
    faces=[(row*m+col,(row+1)*m+col,(row+1)*m+col+1,row*m+col+1)
           for row in range(n-1) for col in range(m-1)]
    mesh=bpy.data.meshes.new('terrain-source');mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('Terrain',mesh);bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=True
    return obj


def simple_material(name,color,roughness=.8):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1)
    bsdf.inputs['Roughness'].default_value=roughness
    return mat


def build_scene(package,neutral=False):
    package=Path(package);manifest=json.loads((package/'manifest.json').read_text())
    fields=np.load(package/'source/sculpted.npz');heights=fields['height']
    instances=json.loads((package/'source/clasts.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    base=manifest['base_elevation_m'];size=manifest['size_m']
    terrain=terrain_geometry(heights,size,base)
    attribute=terrain.data.color_attributes.new(name='Style fields',type='FLOAT_COLOR',domain='POINT')
    packed=np.stack([fields['crust'],fields['dust'],fields['cavity'],np.ones_like(heights)],axis=-1).astype('float32')
    attribute.data.foreach_set('color',packed.ravel())
    clay=simple_material('Ochre clay',(.42,.28,.13) if not neutral else (.45,.42,.37),.62)
    dark=simple_material('Dark crumbly aggregate',(.15,.135,.105) if not neutral else (.45,.42,.37))
    if not neutral:
        tree=dark.node_tree;bsdf=tree.nodes.get('Principled BSDF')
        coords=tree.nodes.new('ShaderNodeTexCoord')
        pits=tree.nodes.new('ShaderNodeTexNoise');pits.inputs['Scale'].default_value=18
        pits.inputs['Detail'].default_value=4;pits.inputs['Roughness'].default_value=.8
        tree.links.new(coords.outputs['Object'],pits.inputs['Vector'])
        bump=tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.8;bump.inputs['Distance'].default_value=2.0
        tree.links.new(pits.outputs['Fac'],bump.inputs['Height']);tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
        variation=tree.nodes.new('ShaderNodeValToRGB');variation.color_ramp.elements[0].color=(.07,.06,.045,1)
        variation.color_ramp.elements[1].color=(.26,.235,.19,1)
        tree.links.new(pits.outputs['Fac'],variation.inputs[0]);tree.links.new(variation.outputs[0],bsdf.inputs['Base Color'])
    terrain.data.materials.append(clay)
    if not neutral:
        # These physical-scale nodes are source authoring; standard export bakes
        # their character into images. The source view can resolve fine clay relief.
        tree=clay.node_tree;bsdf=tree.nodes.get('Principled BSDF')
        coordinates=tree.nodes.new('ShaderNodeTexCoord')
        fine=tree.nodes.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=.85
        fine.inputs['Detail'].default_value=3.5;fine.inputs['Roughness'].default_value=.7
        tree.links.new(coordinates.outputs['Object'],fine.inputs['Vector'])
        rough=tree.nodes.new('ShaderNodeBump');rough.inputs['Strength'].default_value=.35
        rough.inputs['Distance'].default_value=.4
        tree.links.new(fine.outputs['Fac'],rough.inputs['Height'])
        folds=tree.nodes.new('ShaderNodeTexNoise');folds.inputs['Scale'].default_value=.095
        folds.inputs['Detail'].default_value=4
        tree.links.new(coordinates.outputs['Object'],folds.inputs['Vector'])
        coarse=tree.nodes.new('ShaderNodeBump');coarse.inputs['Strength'].default_value=.3
        coarse.inputs['Distance'].default_value=.7
        tree.links.new(folds.outputs['Fac'],coarse.inputs['Height']);tree.links.new(rough.outputs['Normal'],coarse.inputs['Normal'])
        tree.links.new(coarse.outputs['Normal'],bsdf.inputs['Normal'])
        tint=tree.nodes.new('ShaderNodeValToRGB')
        tint.color_ramp.elements[0].color=(.35,.25,.13,1);tint.color_ramp.elements[1].color=(.62,.45,.26,1)
        tree.links.new(folds.outputs['Fac'],tint.inputs[0])
        attr=tree.nodes.new('ShaderNodeAttribute');attr.attribute_name='Style fields'
        separate=tree.nodes.new('ShaderNodeSeparateColor');tree.links.new(attr.outputs['Color'],separate.inputs['Color'])
        clay_mix=tree.nodes.new('ShaderNodeMixRGB');clay_mix.inputs[1].default_value=(.095,.09,.075,1)
        tree.links.new(separate.outputs['Red'],clay_mix.inputs[0]);tree.links.new(tint.outputs[0],clay_mix.inputs[2])
        dust_amount=tree.nodes.new('ShaderNodeMath');dust_amount.operation='MULTIPLY';dust_amount.inputs[1].default_value=.4
        tree.links.new(separate.outputs['Green'],dust_amount.inputs[0])
        dust_mix=tree.nodes.new('ShaderNodeMixRGB');dust_mix.inputs[2].default_value=(.72,.65,.52,1)
        tree.links.new(dust_amount.outputs[0],dust_mix.inputs[0]);tree.links.new(clay_mix.outputs[0],dust_mix.inputs[1])
        tree.links.new(dust_mix.outputs[0],bsdf.inputs['Base Color'])
        wet_rough=tree.nodes.new('ShaderNodeMapRange');wet_rough.inputs['From Min'].default_value=0;wet_rough.inputs['From Max'].default_value=1
        wet_rough.inputs['To Min'].default_value=.8;wet_rough.inputs['To Max'].default_value=.55
        tree.links.new(separate.outputs['Red'],wet_rough.inputs['Value']);tree.links.new(wet_rough.outputs[0],bsdf.inputs['Roughness'])
    # Twelve reproducible irregular clast shapes, instanced rather than duplicated.
    templates=[]
    for i in range(12):
        mesh=make_clast_mesh(4271,i);mesh.materials.append(dark);templates.append(mesh)
    for c in instances:
        obj=bpy.data.objects.new(c['id'],templates[int(c['shape_id'].split('-')[-1])])
        bpy.context.collection.objects.link(obj)
        x,h,z=c['position_m'];rx,ry,rz=c['radii_m'];obj.location=(x,-z,h-base)
        obj.scale=(rx,rz,ry)
        q=c['orientation_xyzw'];obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Quaternion((q[3],q[0],-q[2],q[1]))
    water_path=package/'source/water-mesh.npz'
    if water_path.exists():
        data=np.load(water_path);positions=data['positions'];faces=data['triangles'].copy()
        points=np.c_[positions[:,0],-positions[:,2],positions[:,1]]
        cross=np.cross(points[faces[:,1]]-points[faces[:,0]],points[faces[:,2]]-points[faces[:,0]])
        faces[cross[:,2]<0]=faces[cross[:,2]<0][:,[0,2,1]]
        mesh=bpy.data.meshes.new('Silty channel');mesh.from_pydata(points.tolist(),[],faces.tolist());mesh.update()
        obj=bpy.data.objects.new('Mapped pale water',mesh);bpy.context.collection.objects.link(obj)
        water=simple_material('Opaque warm silt',(1.0,.94,.78),.88)
        obj.data.materials.append(water);obj['style_role']='water'
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.world.color=(.22,.22,.22)
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.76,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.18
    bpy.ops.object.light_add(type='SUN',location=(-800,-500,600));sun=bpy.context.object
    sun.name='Warm soft key';sun.data.energy=2.4;sun.data.angle=.065
    sun.data.color=(1,.86,.69);aim(sun,(0,0,0))
    bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera
    camera.data.type='PERSP';camera.data.lens_unit='FOV';camera.data.angle=math.radians(40)
    camera.data.clip_end=20000
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=1.0
    return manifest,terrain


def set_camera(manifest,name):
    pose=manifest['cameras'][name];x,y,z=pose['target'];target=Vector((x,-z,y))
    yaw=math.radians(pose['yaw_deg']);pitch=math.radians(pose['pitch_deg']);d=pose['distance']
    camera=bpy.context.scene.camera
    camera.location=target+Vector((d*math.sin(yaw)*math.cos(pitch),-d*math.cos(yaw)*math.cos(pitch),d*math.sin(pitch)))
    aim(camera,target);camera.data.angle=math.radians(pose['fov_y_deg'])


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--neutral',action='store_true');parser.add_argument('--views',default='elevated,close,overhead')
    parsed=parser.parse_args(args);manifest,_=build_scene(parsed.package,parsed.neutral)
    for name in parsed.views.split(','):
        set_camera(manifest,name)
        bpy.context.scene.render.filepath=str((parsed.package/'review'/f'{"clay" if parsed.neutral else "source"}-{name}.png').resolve())
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str((parsed.package/'source/master.blend').resolve()))


if __name__=='__main__':main()
