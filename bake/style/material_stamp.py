"""Bake a coherent granular material stamp from actual authored geometry."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector
sys.path.insert(0, str(Path(__file__).resolve().parent))
from clast_mesh import make_clast_mesh


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resolution',type=int,default=2048);parser.add_argument('--span',type=float,default=64)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    span=args.span;rng=np.random.default_rng(81571);templates=[make_clast_mesh(81571,i) for i in range(12)]
    bpy.ops.mesh.primitive_plane_add(size=span*3,location=(span/2,span/2,0));floor=bpy.context.object
    objects=[floor]
    for i in range(950):
        x,y=rng.uniform(0,span,2);radius=np.clip(rng.lognormal(np.log(1.45),.5),.45,3.5)
        angle=rng.uniform(0,math.pi*2); aspect=rng.uniform(.8,1.2)
        for dx in [-span,0,span]:
            for dy in [-span,0,span]:
                cx,cy=x+dx,y+dy
                if not (-radius*1.5<cx<span+radius*1.5 and -radius*1.5<cy<span+radius*1.5):continue
                obj=bpy.data.objects.new(f'fragment-{i}-{dx}-{dy}',templates[i%12]);bpy.context.collection.objects.link(obj)
                obj.location=(cx,cy,radius*.1);obj.scale=(radius,radius*aspect,radius*.8)
                obj.rotation_euler[2]=angle;objects.append(obj)
    mat=bpy.data.materials.new('Linear geometry data');mat.use_nodes=True
    for obj in objects:obj.data.materials.clear();obj.data.materials.append(mat)
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    output=nodes.new('ShaderNodeOutputMaterial');emission=nodes.new('ShaderNodeEmission');links.new(emission.outputs[0],output.inputs[0])
    geometry=nodes.new('ShaderNodeNewGeometry');separate=nodes.new('ShaderNodeSeparateXYZ');links.new(geometry.outputs['Position'],separate.inputs[0])
    height=nodes.new('ShaderNodeMath');height.operation='DIVIDE';height.inputs[1].default_value=5.;links.new(separate.outputs['Z'],height.inputs[0])
    encode=nodes.new('ShaderNodeVectorMath');encode.operation='SCALE';encode.inputs['Scale'].default_value=.5;links.new(geometry.outputs['Normal'],encode.inputs[0])
    add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';add.inputs[1].default_value=(.5,.5,.5);links.new(encode.outputs['Vector'],add.inputs[0])
    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=3.;ao.samples=16
    bpy.ops.object.camera_add(location=(span/2,span/2,100));camera=bpy.context.object;camera.rotation_euler=(0,0,0)
    camera.data.type='ORTHO';camera.data.ortho_scale=span
    scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.use_denoising=False
    scene.render.resolution_x=args.resolution;scene.render.resolution_y=args.resolution;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='OPEN_EXR';scene.render.image_settings.color_mode='RGBA';scene.render.image_settings.color_depth='32'
    scene.view_settings.view_transform='Raw';scene.view_settings.exposure=0
    arrays={}
    for name,socket,samples in [('height',height.outputs[0],1),('normal',add.outputs['Vector'],1),('ao',ao.outputs['AO'],16)]:
        links.new(socket,emission.inputs['Color']);scene.cycles.samples=samples
        scene.render.filepath=str(out/f'{name}.exr');bpy.ops.render.render(write_still=True)
        image=bpy.data.images.load(str(out/f'{name}.exr'),check_existing=False);image.colorspace_settings.name='Non-Color'
        pixels=np.asarray(image.pixels[:],dtype='float32').reshape(args.resolution,args.resolution,4)
        values=np.flipud(pixels[:,:,:3]).copy()
        if name=='height':values=values[:,:,0]*5.
        elif name=='ao':values=values[:,:,0]
        arrays[name]=values;bpy.data.images.remove(image)
        print(f'{name}: min {values.min():.4f}, max {values.max():.4f}',flush=True)
    np.savez_compressed(out/'maps.npz',**arrays)
    (out/'manifest.json').write_text(json.dumps({'seed':81571,'span_m':span,'resolution':args.resolution,
          'height_range_m':[float(arrays['height'].min()),float(arrays['height'].max())],
          'normal_convention':'opengl-positive-y','source':'authored fractured geometry; linear emission height/normal and ray-traced AO',
          'geometry_count':len(objects),'view_transform':'Raw','exposure':0},indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'source.blend'))


if __name__=='__main__':main()
