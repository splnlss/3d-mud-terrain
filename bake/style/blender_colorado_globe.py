"""Portable Colorado crown export and review renders, run with Blender Python."""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector


CAP_ANGLE = math.radians(46)  # keep in step with colorado_globe.CAP_ANGLE
SPHERE = .8 / math.sin(CAP_ANGLE); CENTRE = Vector((0, 0, -SPHERE * math.cos(CAP_ANGLE)))
# Presentation only: never exported. Sun sits behind the crown, slightly right of centre, low enough for the ridge to hide most of it.
SUN_POS = Vector((.30, 1.7, .44)); HALO_REACH = SPHERE * 1.7; GLOW = 1.2; HALO = 3.0
# Thin bright atmosphere band hugging the planet's limb, like Earth seen from orbit: width and strength.
RIM_WIDTH = .035; RIM = 3.0
# Dry clay: matte mud, barely damp rivers. Roughness and specular level are exported with the GLB materials.
MUD_ROUGHNESS = .95; RIVER_ROUGHNESS = .6; SPECULAR_LEVEL = .2


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def material(name, color, rough, specular=SPECULAR_LEVEL):
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF'); bsdf.inputs['Base Color'].default_value=(*color,1); bsdf.inputs['Roughness'].default_value=rough; bsdf.inputs['Specular IOR Level'].default_value=specular
    return mat


def presentation():
    """Atmosphere behind the globe (broad halo plus a thin limb band) and a warm sunrise glow, matching src/colorado-atmosphere.ts. Scene-only: never exported."""
    bpy.ops.mesh.primitive_circle_add(vertices=96, radius=HALO_REACH * 1.05, fill_type='NGON'); halo = bpy.context.object; halo.name = 'Atmosphere halo'
    mat = bpy.data.materials.new('Atmosphere glow'); mat.use_nodes = True; nodes = mat.node_tree.nodes; links = mat.node_tree.links; nodes.clear()
    def math_node(op, a, b=None):
        m = nodes.new('ShaderNodeMath'); m.operation = op
        for i, v in enumerate([a, b]):
            if v is None: continue
            if isinstance(v, (int, float)): m.inputs[i].default_value = v
            else: links.new(v, m.inputs[i])
        return m.outputs[0]
    coord = nodes.new('ShaderNodeTexCoord'); length = nodes.new('ShaderNodeVectorMath'); length.operation = 'LENGTH'; links.new(coord.outputs['Object'], length.inputs[0])
    # Brightest at the limb, cubic fade to nothing at HALO_REACH; hidden behind the globe inside the limb.
    fade = nodes.new('ShaderNodeMapRange'); fade.inputs['From Min'].default_value = SPHERE * .97; fade.inputs['From Max'].default_value = HALO_REACH; fade.inputs['To Min'].default_value = 1; fade.inputs['To Max'].default_value = 0; links.new(length.outputs['Value'], fade.inputs['Value'])
    profile = math_node('POWER', fade.outputs[0], 3)
    geo = nodes.new('ShaderNodeNewGeometry'); xyz = nodes.new('ShaderNodeSeparateXYZ'); links.new(geo.outputs['Position'], xyz.inputs[0])
    gate = nodes.new('ShaderNodeMapRange'); gate.interpolation_type = 'SMOOTHSTEP'; gate.inputs['From Min'].default_value = .0; gate.inputs['From Max'].default_value = .45; links.new(xyz.outputs['Z'], gate.inputs['Value'])
    direction = nodes.new('ShaderNodeVectorMath'); direction.operation = 'NORMALIZE'; links.new(coord.outputs['Object'], direction.inputs[0])
    toward = nodes.new('ShaderNodeVectorMath'); toward.operation = 'DOT_PRODUCT'; toward.name = 'Sun direction'; links.new(direction.outputs[0], toward.inputs[0])
    warm = math_node('POWER', math_node('MAXIMUM', toward.outputs['Value'], 0), 24)
    rim = nodes.new('ShaderNodeEmission'); rim.inputs['Color'].default_value = (.45, .66, 1, 1); links.new(math_node('MULTIPLY', math_node('MULTIPLY', profile, gate.outputs[0]), GLOW), rim.inputs['Strength'])
    amber = nodes.new('ShaderNodeEmission'); amber.inputs['Color'].default_value = (1, .55, .22, 1); links.new(math_node('MULTIPLY', math_node('MULTIPLY', math_node('MULTIPLY', profile, warm), gate.outputs[0]), HALO), amber.inputs['Strength'])
    # Limb band: rises right at the limb, falls off exponentially over RIM_WIDTH sphere radii.
    over = math_node('SUBTRACT', math_node('DIVIDE', length.outputs['Value'], SPHERE), 1.0)
    band = math_node('MULTIPLY', math_node('EXPONENT', math_node('DIVIDE', math_node('MAXIMUM', over, 0), -RIM_WIDTH)), math_node('GREATER_THAN', over, -.004))
    # The band follows the upper arc of the limb (angle from the halo's up axis), fading out toward where the planet meets the ground.
    # Height of the sphere's tangent (horizon) point in this direction; the band exists only where that horizon is above ground.
    sep = nodes.new('ShaderNodeSeparateXYZ'); links.new(coord.outputs['Object'], sep.inputs[0]); radius = math_node('MAXIMUM', length.outputs['Value'], 1e-4)
    horizon = nodes.new('ShaderNodeValue'); horizon.name = 'Limb height'; right_z = nodes.new('ShaderNodeValue'); right_z.name = 'Right z'; up_z = nodes.new('ShaderNodeValue'); up_z.name = 'Up z'
    tilt = math_node('ADD', math_node('MULTIPLY', math_node('DIVIDE', sep.outputs['X'], radius), right_z.outputs[0]), math_node('MULTIPLY', math_node('DIVIDE', sep.outputs['Y'], radius), up_z.outputs[0]))
    arc = nodes.new('ShaderNodeMapRange'); arc.interpolation_type = 'SMOOTHSTEP'; arc.inputs['From Min'].default_value = .06; arc.inputs['From Max'].default_value = .24
    limb_r = nodes.new('ShaderNodeValue'); limb_r.name = 'Limb radius'; horizon_y = math_node('ADD', horizon.outputs[0], math_node('MULTIPLY', tilt, limb_r.outputs[0])); links.new(horizon_y, arc.inputs['Value'])
    # Glow only behind the emerging planet: the soft ground fade times a fade out along the planet's lower sides (planet horizon height).
    sides = nodes.new('ShaderNodeMapRange'); sides.interpolation_type = 'SMOOTHSTEP'; sides.inputs['From Min'].default_value = .05; sides.inputs['From Max'].default_value = .4; links.new(horizon_y, sides.inputs['Value'])
    for node in (rim, amber):
        strength = node.inputs['Strength'].links[0].from_node; links.new(math_node('MULTIPLY', strength.outputs[0], sides.outputs[0]), node.inputs['Strength'])
    limb = nodes.new('ShaderNodeEmission'); limb.inputs['Color'].default_value = (.55, .82, 1, 1); links.new(math_node('MULTIPLY', math_node('MULTIPLY', band, arc.outputs[0]), RIM), limb.inputs['Strength'])
    add0 = nodes.new('ShaderNodeAddShader'); links.new(rim.outputs[0], add0.inputs[0]); links.new(limb.outputs[0], add0.inputs[1])
    add1 = nodes.new('ShaderNodeAddShader'); links.new(add0.outputs[0], add1.inputs[0]); links.new(amber.outputs[0], add1.inputs[1])
    clear = nodes.new('ShaderNodeBsdfTransparent'); add2 = nodes.new('ShaderNodeAddShader'); links.new(add1.outputs[0], add2.inputs[0]); links.new(clear.outputs[0], add2.inputs[1])
    out = nodes.new('ShaderNodeOutputMaterial'); links.new(add2.outputs[0], out.inputs['Surface']); halo.data.materials.append(mat)
    for flag in ['visible_shadow', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter']: setattr(halo, flag, False)
    bpy.ops.object.light_add(type='SUN', location=SUN_POS); back = bpy.context.object; back.name = 'Warm back light'; back.data.energy = 1.2; back.data.color = (1, .72, .45); back.data.angle = math.radians(4); aim(back, (0, 0, .3))
    return halo


def place_halo(halo, eye):
    """Stand the halo one sphere radius behind the globe centre, facing the camera, scaled so its limb still lines up in perspective."""
    eye = Vector(eye); away = (CENTRE - eye).normalized(); halo.location = CENTRE + away * SPHERE; aim(halo, eye)
    # Exact perspective limb: the tangent cone through the sphere meets the halo plane at radius SPHERE in local units.
    d = (CENTRE - eye).length; halo.scale = [(halo.location - eye).length / math.sqrt(d * d - SPHERE * SPHERE)] * 3
    bpy.context.view_layer.update()
    nodes = halo.data.materials[0].node_tree.nodes; basis = halo.matrix_world.to_3x3().normalized()
    nodes['Limb height'].outputs[0].default_value = CENTRE.z - away.z * SPHERE * SPHERE / d; nodes['Limb radius'].outputs[0].default_value = SPHERE * math.sqrt(1 - (SPHERE / d) ** 2)
    nodes['Right z'].outputs[0].default_value = basis.col[0].z; nodes['Up z'].outputs[0].default_value = basis.col[1].z
    local = halo.matrix_world.to_3x3().inverted() @ (SUN_POS - CENTRE); local.z = 0
    halo.data.materials[0].node_tree.nodes['Sun direction'].inputs[1].default_value = local.normalized()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--package',type=Path,required=True); parser.add_argument('--samples',type=int,default=48); parser.add_argument('--verify',action='store_true'); parser.add_argument('--preview',action='store_true',help='half-size renders for iteration')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]); root=args.package.resolve()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    if args.verify:
        bpy.ops.import_scene.gltf(filepath=str(root/'colorado-crown.glb'))
        obj=bpy.data.objects['Colorado crown']
    else:
        data=np.load(root/'model.npz'); pos=data['positions']; faces=data['faces']; n=len(pos)
        mesh=bpy.data.meshes.new('Single resolution rounded terrain'); mesh.vertices.add(n); mesh.vertices.foreach_set('co',pos.ravel())
        mesh.loops.add(faces.size); mesh.loops.foreach_set('vertex_index',faces.ravel()); mesh.polygons.add(len(faces)); mesh.polygons.foreach_set('loop_start',np.arange(0,faces.size,4,dtype='int32')); mesh.polygons.foreach_set('loop_total',np.full(len(faces),4,dtype='int32')); mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),bool)); mesh.update()
        attr=mesh.color_attributes.new(name='MudColor',type='FLOAT_COLOR',domain='POINT'); attr.data.foreach_set('color',np.column_stack([data['color'],np.ones(n)]).astype('float32').ravel())
        obj=bpy.data.objects.new('Colorado crown',mesh); bpy.context.collection.objects.link(obj)
        for name,rough in [('Warm mud and dark clumps',MUD_ROUGHNESS),('Mapped narrow rivers',RIVER_ROUGHNESS)]:
            mat=material(name,(.2,.15,.1),rough); node=mat.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name='MudColor'; mat.node_tree.links.new(node.outputs['Color'],mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color']); mesh.materials.append(mat)
        mesh.polygons.foreach_set('material_index',(data['roughness'][faces].mean(1)<.38).astype('int32'))
        # Fine outline is a separate guide object, so consumers can hide it.
        curve=bpy.data.curves.new('Colorado mapped boundary','CURVE'); curve.dimensions='3D'; curve.bevel_depth=.0028; curve.bevel_resolution=2
        coords=np.array(json.loads((root/'border.json').read_text())); spline=curve.splines.new('POLY'); spline.points.add(len(coords)-1); spline.points.foreach_set('co',np.column_stack([coords,np.ones(len(coords))]).ravel())
        border=bpy.data.objects.new('Colorado border',curve); bpy.context.collection.objects.link(border); curve.materials.append(material('Colorado boundary',(.10,.065,.035),.85))
        bpy.ops.object.select_all(action='DESELECT'); border.select_set(True); bpy.context.view_layer.objects.active=border; bpy.ops.object.convert(target='MESH')
        obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(root/'colorado-crown.glb'),export_format='GLB',use_selection=True,export_materials='EXPORT',export_normals=True,export_yup=True)
    halo = presentation()
    # The state outline ships as an optional guide; review renders show the terrain alone.
    for o in bpy.data.objects:
        if o.name.startswith('Colorado border'): o.hide_render = True
    # Ground is scene staging, kept separate from portable terrain asset.
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002)); ground=bpy.context.object; ground.name='Ground plane'; ground.data.materials.append(material('Backdrop',(.012,.010,.008),1,0)); ground.visible_camera=False
    scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=args.samples; scene.cycles.use_denoising=True
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences; prefs.compute_device_type='METAL'; prefs.get_devices()
        for d in prefs.devices: d.use=True
        scene.cycles.device='GPU'
    except Exception: pass
    # Soft warm studio light for the surfaces; camera rays see a dark backdrop so the horizon glow can read.
    world=bpy.data.worlds.new('Soft studio'); world.use_nodes=True; nodes=world.node_tree.nodes; links=world.node_tree.links
    light_bg=nodes['Background']; light_bg.inputs[0].default_value=(.65,.58,.49,1); light_bg.inputs[1].default_value=.65
    dark=nodes.new('ShaderNodeBackground'); dark.inputs[0].default_value=(.03,.026,.02,1); mix=nodes.new('ShaderNodeMixShader'); path=nodes.new('ShaderNodeLightPath')
    links.new(light_bg.outputs[0],mix.inputs[1]); links.new(dark.outputs[0],mix.inputs[2]); links.new(path.outputs['Is Camera Ray'],mix.inputs[0]); links.new(mix.outputs[0],nodes['World Output'].inputs['Surface']); scene.world=world
    bpy.ops.object.light_add(type='AREA',location=(-1.5,-1,3)); light=bpy.context.object; light.data.energy=180; light.data.shape='DISK'; light.data.size=2; light.data.color=(1,.87,.70); aim(light,(0,0,.2))
    bpy.ops.object.camera_add(); camera=bpy.context.object; scene.camera=camera; camera.data.clip_start=.01
    scene.view_settings.view_transform='AgX'; scene.view_settings.look='AgX - Medium High Contrast'
    # Hero: low south-facing perspective like the accepted mockup. Overhead: orthographic north-up map check.
    rio=json.loads((root/'manifest.json').read_text())['border_crossings_model_xyz']['Rio Grande'][0]
    views={'hero':('PERSP',50,(0,-2.55,.50),(0,0,.22),(1600,1000)), 'overhead':('ORTHO',2.1,(0,-.01,3),(0,0,0),(1400,1400)), 'detail':('PERSP',85,(rio[0]-.08,rio[1]-.14,rio[2]+.09),tuple(rio),(1400,1000))}
    for name,(kind,lens,loc,target,size) in views.items():
        if args.verify and name!='hero': continue
        camera.data.type=kind; camera.data.lens=lens if kind=='PERSP' else camera.data.lens; camera.data.ortho_scale=lens if kind=='ORTHO' else camera.data.ortho_scale
        camera.location=loc; aim(camera,target); place_halo(halo,loc); scene.render.resolution_x,scene.render.resolution_y=size; scene.render.resolution_percentage=50 if args.preview else 100
        scene.render.filepath=str(root/(('portable-' if args.verify else '')+name+'.png')); bpy.ops.render.render(write_still=True)
    if not args.verify:
        camera.data.type='PERSP'; camera.data.lens=views['hero'][1]; camera.location=views['hero'][2]; aim(camera,views['hero'][3]); bpy.ops.wm.save_as_mainfile(filepath=str(root/'colorado-crown.blend'))
    else:
        (root/'portable-verification.json').write_text(json.dumps({'imported':True,'vertices':len(obj.data.vertices),'bounds':[list(v) for v in obj.bound_box],'materials':[m.name for m in obj.data.materials],'scene_objects':sorted(o.name for o in bpy.data.objects)},indent=2))


if __name__=='__main__': main()
