"""Render the image-matched relief specimen from saved review cameras (Blender Python)."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
import numpy as np
from mathutils import Vector

# Poses in model metres. `canyon` is framed against reference 04, `elevated` against 01.
# `creek` looks along Culebra Creek on the real patch.
CAMERAS = {
    'canyon': {'location': (-.56, -.96, .50), 'target': (-.02, -.14, .0), 'lens': 62, 'fstop': 8, 'size': (1672, 941)},
    'elevated': {'location': (-.25, -1.6, 1.2), 'target': (0, -.14, 0), 'lens': 72, 'fstop': 16, 'size': (1536, 1024)},
    'creek': {'location': (-.95, -.78, .46), 'target': (-.15, -.24, .0), 'lens': 60, 'fstop': 11, 'size': (1672, 941)},
    'overhead': {'location': (0, -.25, 2.6), 'target': (0, 0, 0), 'lens': 60, 'fstop': 22, 'size': (1200, 1312)},
}


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def use_gpu(scene):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    try:
        prefs.compute_device_type = 'METAL'; prefs.get_devices()
        for device in prefs.devices: device.use = True
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--camera', default='canyon', choices=sorted(CAMERAS)); parser.add_argument('--samples', type=int, default=160)
    parser.add_argument('--clay', action='store_true', help='neutral clay: shape without colour or finish')
    parser.add_argument('--sharp', action='store_true', help='disable depth of field')
    parser.add_argument('--tag'); parser.add_argument('--save-blend', action='store_true')
    parser.add_argument('--water-colour', default='.42,.40,.36', help='linear r,g,b of the Water material')
    parser.add_argument('--water-roughness', type=float, default=.22)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:]); root = args.study.resolve()
    span = json.loads((root / 'manifest.json').read_text())['span_m']
    data = np.load(root / 'surface.npz'); height = data['height']; n, m = height.shape
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    # Image row zero is north, matching the standard material package convention.
    x, y = np.meshgrid(np.linspace(-span / 2, span / 2, m), np.linspace(span / 2, -span / 2, n))
    positions = np.stack([x, y, height], axis=-1).astype('float32')
    indices = np.arange(n * m, dtype='int32').reshape(n, m)
    faces = np.stack([indices[:-1, :-1], indices[1:, :-1], indices[1:, 1:], indices[:-1, 1:]], axis=-1).reshape(-1, 4)
    mesh = bpy.data.meshes.new('Relief specimen surface')
    mesh.vertices.add(n * m); mesh.vertices.foreach_set('co', positions.ravel())
    mesh.loops.add(faces.size); mesh.loops.foreach_set('vertex_index', faces.ravel())
    mesh.polygons.add(len(faces)); mesh.polygons.foreach_set('loop_start', np.arange(0, faces.size, 4, dtype='int32'))
    mesh.polygons.foreach_set('loop_total', np.full(len(faces), 4, dtype='int32'))
    mesh.polygons.foreach_set('use_smooth', np.ones(len(faces), dtype=bool)); mesh.update()
    obj = bpy.data.objects.new('Relief specimen', mesh); bpy.context.collection.objects.link(obj)
    colour = mesh.color_attributes.new(name='Intrinsic colour', type='FLOAT_COLOR', domain='POINT')
    base = np.full((n, m, 3), .18, 'float32') if args.clay else data['base_color']
    colour.data.foreach_set('color', np.concatenate([base, np.ones((n, m, 1), 'float32')], axis=-1).ravel())
    finish = mesh.attributes.new(name='Finish', type='FLOAT', domain='POINT')
    finish.data.foreach_set('value', (np.full((n, m), .6, 'float32') if args.clay else data['roughness']).ravel())
    material = bpy.data.materials.new('Clay, crust and silt'); material.use_nodes = True
    nodes = material.node_tree.nodes; links = material.node_tree.links; bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['IOR'].default_value = 1.5; bsdf.inputs['Specular IOR Level'].default_value = .5
    attr = nodes.new('ShaderNodeAttribute'); attr.attribute_name = colour.name
    links.new(attr.outputs['Color'], bsdf.inputs['Base Color'])
    rough = nodes.new('ShaderNodeAttribute'); rough.attribute_name = finish.name
    links.new(rough.outputs['Fac'], bsdf.inputs['Roughness'])
    # Sub-sample pores only; every larger feature is real geometry.
    geometry = nodes.new('ShaderNodeNewGeometry'); pore = nodes.new('ShaderNodeTexNoise')
    pore.inputs['Scale'].default_value = 1100; pore.inputs['Detail'].default_value = 3
    links.new(geometry.outputs['Position'], pore.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .5; bump.inputs['Distance'].default_value = .0003
    links.new(pore.outputs['Fac'], bump.inputs['Height']); links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    obj.data.materials.append(material)
    # Water is a separate object with its own material, so its look changes without touching the terrain.
    # It sits at the authored water level; the carved bed and banks pass through it to form the shoreline.
    step = 2; level = data['water_level'][::step, ::step]; wet = data['bank'][::step, ::step] < .004; k, l = level.shape
    ids = np.arange(k * l, dtype='int32').reshape(k, l); quad = wet[:-1, :-1] & wet[1:, :-1] & wet[1:, 1:] & wet[:-1, 1:]
    wfaces = np.stack([ids[:-1, :-1], ids[1:, :-1], ids[1:, 1:], ids[:-1, 1:]], axis=-1)[quad]
    if len(wfaces) and not args.clay:
        used, remap = np.unique(wfaces, return_inverse=True); wfaces = remap.reshape(-1, 4).astype('int32')
        wpos = np.stack([x[::step, ::step], y[::step, ::step], level], axis=-1).reshape(-1, 3)[used].astype('float32')
        wmesh = bpy.data.meshes.new('Water surface'); wmesh.vertices.add(len(wpos)); wmesh.vertices.foreach_set('co', wpos.ravel())
        wmesh.loops.add(wfaces.size); wmesh.loops.foreach_set('vertex_index', wfaces.ravel())
        wmesh.polygons.add(len(wfaces)); wmesh.polygons.foreach_set('loop_start', np.arange(0, wfaces.size, 4, dtype='int32'))
        wmesh.polygons.foreach_set('loop_total', np.full(len(wfaces), 4, dtype='int32'))
        wmesh.polygons.foreach_set('use_smooth', np.ones(len(wfaces), dtype=bool)); wmesh.update()
        water = bpy.data.objects.new('Water', wmesh); bpy.context.collection.objects.link(water)
        wmat = bpy.data.materials.new('Water'); wmat.use_nodes = True; wbsdf = wmat.node_tree.nodes.get('Principled BSDF')
        wbsdf.inputs['Base Color'].default_value = (*[float(v) for v in args.water_colour.split(',')], 1)
        wbsdf.inputs['Roughness'].default_value = args.water_roughness; wbsdf.inputs['IOR'].default_value = 1.33
        water.data.materials.append(wmat)
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; use_gpu(scene)
    scene.cycles.samples = args.samples; scene.cycles.use_denoising = True
    pose = CAMERAS[args.camera]
    scene.render.resolution_x, scene.render.resolution_y = pose['size']; scene.render.resolution_percentage = 100
    world = bpy.data.worlds.new('Warm room fill'); scene.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs[0].default_value = (.80, .66, .50, 1)
    world.node_tree.nodes['Background'].inputs[1].default_value = .7
    sun_from = Vector((.95, .80, .34)).normalized()
    bpy.ops.object.light_add(type='SUN', location=sun_from * 3); sun = bpy.context.object
    sun.data.energy = 4.0; sun.data.angle = math.radians(7); sun.data.color = (1, .80, .56); aim(sun, (0, 0, 0))
    bpy.ops.object.camera_add(location=pose['location']); camera = bpy.context.object; scene.camera = camera
    aim(camera, pose['target']); camera.data.lens = pose['lens']; camera.data.clip_start = .01; camera.data.clip_end = 50
    bpy.ops.object.empty_add(location=pose['target']); focus = bpy.context.object; focus.name = 'Focal plane'
    camera.data.dof.use_dof = not args.sharp; camera.data.dof.focus_object = focus; camera.data.dof.aperture_fstop = pose['fstop']
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = .55
    tag = args.tag or f"{args.camera}{'-clay' if args.clay else ''}{'-sharp' if args.sharp else ''}"
    scene.render.filepath = str(root / f'{tag}.png'); bpy.ops.render.render(write_still=True)
    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(root / f'{tag}.blend'))
    (root / f'{tag}-settings.json').write_text(json.dumps({'camera': args.camera, **pose, 'samples': args.samples,
        'sun_direction': list(sun_from), 'sun_energy': 4.0, 'sun_angle_deg': 7, 'sun_colour': [1, .80, .56],
        'world_colour': [.80, .66, .50], 'world_strength': .7, 'view': 'AgX - Medium High Contrast', 'exposure': .55,
        'water_colour': args.water_colour, 'water_roughness': args.water_roughness, 'neutral_clay': args.clay, 'depth_of_field': not args.sharp, 'vertices': int(n * m),
        'note': 'Calibration specimen; not the San Luis DEM'}, indent=2) + '\n')


if __name__ == '__main__': main()
