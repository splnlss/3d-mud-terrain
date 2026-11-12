"""Blender source-scene preview. Run with Blender's Python, not the bake venv."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Vector,Quaternion


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
    heights=np.load(package/'source/sculpted.npz')['height']
    instances=json.loads((package/'source/clasts.json').read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    base=manifest['base_elevation_m'];size=manifest['size_m']
    terrain=terrain_geometry(heights,size,base)
    clay=simple_material('Ochre clay',(.42,.28,.13) if not neutral else (.45,.42,.37))
    dark=simple_material('Dark crumbly aggregate',(.15,.135,.105) if not neutral else (.45,.42,.37))
    terrain.data.materials.append(clay)
    # Twelve reproducible irregular clast shapes, instanced rather than duplicated.
    templates=[]
    for i in range(12):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
        obj=bpy.context.object;mesh=obj.data
        rng=np.random.default_rng(4271+i)
        for v in mesh.vertices:
            d=v.co.normalized();v.co*=float(rng.uniform(.85,1.13))
            # Flattened fractured underside and directional worn facets.
            v.co.z=max(v.co.z,-.65)
        for face in mesh.polygons:face.use_smooth=True
        mesh.materials.append(dark);templates.append(mesh)
        bpy.data.objects.remove(obj,do_unlink=True)
    for c in instances:
        obj=bpy.data.objects.new(c['id'],templates[int(c['shape_id'].split('-')[-1])])
        bpy.context.collection.objects.link(obj)
        x,h,z=c['position_m'];rx,ry,rz=c['radii_m'];obj.location=(x,-z,h-base)
        obj.scale=(rx,rz,ry)
        q=c['orientation_xyzw'];obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Quaternion((q[3],q[0],-q[2],q[1]))
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=32
    scene.cycles.use_denoising=True
    scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.world.color=(.22,.22,.22)
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.69,.76,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.3
    bpy.ops.object.light_add(type='SUN',location=(-800,-500,1000));sun=bpy.context.object
    sun.name='Warm soft key';sun.data.energy=2.4;sun.data.angle=.14
    sun.data.color=(1,.86,.69);aim(sun,(0,0,0))
    bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera
    camera.data.type='PERSP';camera.data.lens_unit='FOV';camera.data.angle=math.radians(40)
    camera.data.clip_end=20000
    scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
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
