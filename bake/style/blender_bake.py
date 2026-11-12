"""Export standard material GLBs or inspect them in an entirely fresh Blender scene."""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
import numpy as np
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_preview import build_scene,set_camera,terrain_geometry,simple_material


def texture_node(material,package,path,linear=False):
    image=bpy.data.images.load(str((package/path).resolve()),check_existing=True)
    image.colorspace_settings.name='Non-Color' if linear else 'sRGB'
    node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
    return node


def pbr_material(package,name,maps):
    material=simple_material(name,(.6,.5,.35));tree=material.node_tree;bsdf=tree.nodes.get('Principled BSDF')
    color=texture_node(material,package,maps['base_color']);tree.links.new(color.outputs['Color'],bsdf.inputs['Base Color'])
    normal=texture_node(material,package,maps['normal'],True);decode=tree.nodes.new('ShaderNodeNormalMap')
    tree.links.new(normal.outputs['Color'],decode.inputs['Color']);tree.links.new(decode.outputs['Normal'],bsdf.inputs['Normal'])
    if 'orm' in maps:
        orm=texture_node(material,package,maps['orm'],True);split=tree.nodes.new('ShaderNodeSeparateColor')
        tree.links.new(orm.outputs['Color'],split.inputs['Color']);tree.links.new(split.outputs['Green'],bsdf.inputs['Roughness'])
        # Recognised glTF occlusion export group, not baked direct lighting.
        group=bpy.data.node_groups.get('glTF Material Output')
        if group is None:
            group=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
            group.interface.new_socket(name='Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
        output=tree.nodes.new('ShaderNodeGroup');output.node_tree=group
        tree.links.new(split.outputs['Red'],output.inputs['Occlusion'])
    else:
        rough=texture_node(material,package,maps['roughness'],True);tree.links.new(rough.outputs['Color'],bsdf.inputs['Roughness'])
    return material


def planar_uv(obj,bounds):
    west,south,east,north=bounds
    uv=obj.data.uv_layers.new(name='UVMap')
    for face in obj.data.polygons:
        for loop in face.loop_indices:
            v=obj.data.vertices[obj.data.loops[loop].vertex_index].co
            uv.data[loop].uv=((v.x-west)/(east-west),(v.y-south)/(north-south))


def bounds_gltf(objects):
    points=[obj.matrix_world@v.co for obj in objects for v in obj.data.vertices]
    positions=np.array([[p.x,p.z,-p.y] for p in points])
    return [positions.min(axis=0).tolist(),positions.max(axis=0).tolist()]


def bake(package):
    manifest,original=build_scene(package)
    source=np.load(package/'source/sculpted.npz')['height'];size=manifest['size_m'];base=manifest['base_elevation_m']
    clasts=[obj for obj in bpy.context.scene.objects if obj.type=='MESH' and obj!=original and obj.get('style_role')!='water']
    waters=[obj for obj in bpy.context.scene.objects if obj.get('style_role')=='water']
    # Source clasts get standard UV/PBR materials, never viewer-only shading.
    granular=next(m for m in manifest['materials'] if m['kind']=='granular')
    clast_mat=pbr_material(package,'Granular clasts',granular['maps'])
    for mesh in {obj.data for obj in clasts}:
        mesh.materials.clear();mesh.materials.append(clast_mat)
        # Spherical UVs are baked on each reusable source shape; split at wrap seam.
        # Smart projection keeps closed sides and ends without world-projection stretch.
        temp=bpy.data.objects.new('uv-author',mesh);bpy.context.collection.objects.link(temp)
        bpy.ops.object.select_all(action='DESELECT');temp.select_set(True);bpy.context.view_layer.objects.active=temp
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.03)
        bpy.ops.object.mode_set(mode='OBJECT');bpy.data.objects.remove(temp,do_unlink=True)
    original.hide_render=True;original.hide_set(True)
    lods=[]
    for cell in manifest['cells']:
        row0,row1,col0,col1=cell['source_window'];bounds=cell['bounds_xnorth_m'];span=bounds[2]-bounds[0]
        obj=terrain_geometry(source[row0:row1+1,col0:col1+1],span,base)
        obj.name=f'Terrain-{cell["id"]}'
        # terrain_geometry is cell-centred; bake absolute patch coordinates in vertices.
        for v in obj.data.vertices:v.co.x+=(bounds[0]+bounds[2])/2;v.co.y+=(bounds[1]+bounds[3])/2
        planar_uv(obj,bounds);obj.data.materials.append(pbr_material(package,f'Clay-{cell["id"]}',cell['maps']))
        selected=[obj]
        for clast in clasts:
            x,y,_=clast.location
            # Assign each centre to exactly one cell, including outward edge clasts.
            cx=min(max(x,-size/2+1e-3),size/2-1e-3);cy=min(max(y,-size/2+1e-3),size/2-1e-3)
            if bounds[0]<=cx<bounds[2] and bounds[1]<=cy<bounds[3]:selected.append(clast)
        # Export a material-batched cell while preserving editable source instances.
        copies=[obj]
        for source_clast in selected[1:]:
            clone=source_clast.copy();clone.data=source_clast.data.copy()
            bpy.context.collection.objects.link(clone);copies.append(clone)
        bpy.ops.object.select_all(action='DESELECT')
        for mesh in copies:mesh.hide_set(False);mesh.select_set(True)
        bpy.context.view_layer.objects.active=obj
        bpy.ops.object.join();bpy.context.view_layer.update()
        path=f'meshes/cell-{cell["id"]}.glb'
        bound=bounds_gltf([obj])
        bpy.ops.export_scene.gltf(filepath=str((package/path).resolve()),export_format='GLB',
            use_selection=True,export_tangents=True,export_yup=True,export_cameras=False,export_lights=False)
        lods.append({'id':cell['id'],'path':path,'level':'master','geometric_error_m':0,
                     'bounds_m':bound,'texture_dimensions':[cell['texture_size']]*2,'parent':None})
        cell['mesh']=path
        print(f'Exported {path} with {len(selected)-1} clasts batched by material',flush=True)
        bpy.data.objects.remove(obj,do_unlink=True)
    if waters:
        bpy.ops.object.select_all(action='DESELECT')
        for water in waters:water.select_set(True)
        bpy.context.view_layer.update()
        path='meshes/water.glb'
        bpy.ops.export_scene.gltf(filepath=str((package/path).resolve()),export_format='GLB',
            use_selection=True,export_yup=True,export_cameras=False,export_lights=False)
        manifest['water'].update(mesh=path,bounds_m=bounds_gltf(waters))
    original.hide_render=False;original.hide_set(False)
    # Editable source remains portable: store image paths relative to saved .blend.
    bpy.ops.wm.save_as_mainfile(filepath=str((package/'source/master.blend').resolve()))
    for image in bpy.data.images:
        if image.filepath:image.filepath=bpy.path.relpath(image.filepath)
    bpy.ops.wm.save_as_mainfile(filepath=str((package/'source/master.blend').resolve()))
    manifest['lods']=lods;manifest['exports_status']='ready'
    (package/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


def verify(package,views):
    manifest,_=build_scene(package)
    for obj in list(bpy.context.scene.objects):
        if obj.type=='MESH':bpy.data.objects.remove(obj,do_unlink=True)
    for cell in manifest['cells']:
        bpy.ops.import_scene.gltf(filepath=str((package/cell['mesh']).resolve()))
    for name in views:
        set_camera(manifest,name)
        bpy.context.scene.render.filepath=str((package/'review'/f'portable-{name}.png').resolve())
        bpy.ops.render.render(write_still=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--action',choices=['bake','verify'],required=True)
    parser.add_argument('--views',default='close,elevated,overhead')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.action=='bake':bake(args.package)
    else:verify(args.package,args.views.split(','))


if __name__=='__main__':main()
