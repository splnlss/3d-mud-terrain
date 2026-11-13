"""Apply geometry-derived granular maps to the source scene and render a draft.

Run in Blender after material_stamp.py; the editable master is left intact.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_preview import set_camera


def apply_texture(terrain, stamp):
    """World scale UVs; normal and AO remain independently inspectable maps."""
    stamp = Path(stamp).resolve()
    meta = json.loads((stamp/'manifest.json').read_text())
    span = meta['span_m']
    mesh = terrain.data
    vertices = np.empty(len(mesh.vertices)*3, dtype='float32')
    mesh.vertices.foreach_get('co', vertices)
    indices = np.empty(len(mesh.loops), dtype='int32')
    mesh.loops.foreach_get('vertex_index', indices)
    uv = mesh.uv_layers.get('Granular physical UV') or mesh.uv_layers.new(name='Granular physical UV')
    uv.data.foreach_set('uv', (vertices.reshape(-1,3)[indices,:2]/span).ravel())
    material = terrain.data.materials[0]
    nodes = material.node_tree.nodes; links = material.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    coords = nodes.new('ShaderNodeUVMap'); coords.uv_map = uv.name
    def image(name):
        node = nodes.new('ShaderNodeTexImage'); node.label = f'Geometry-derived {name}'
        node.image = bpy.data.images.load(str(stamp/f'{name}.exr'), check_existing=True)
        node.image.colorspace_settings.name = 'Non-Color'; node.extension = 'REPEAT'
        links.new(coords.outputs['UV'], node.inputs['Vector'])
        return node
    normal = image('normal')
    normal_map = nodes.new('ShaderNodeNormalMap'); normal_map.uv_map = uv.name
    normal_map.inputs['Strength'].default_value = .85
    links.new(normal.outputs['Color'], normal_map.inputs['Color'])
    links.new(normal_map.outputs['Normal'], bsdf.inputs['Normal'])
    # Cavity shading stays separate from the intrinsic material colour.
    ao = image('ao')
    prior_colour = bsdf.inputs['Base Color'].links[0].from_socket
    cavity = nodes.new('ShaderNodeMixRGB'); cavity.blend_type = 'MULTIPLY'
    cavity.inputs[0].default_value = .75
    links.new(prior_colour, cavity.inputs[1]); links.new(ao.outputs['Color'], cavity.inputs[2])
    links.new(cavity.outputs[0], bsdf.inputs['Base Color'])
    height = image('height')
    roughness = nodes.new('ShaderNodeMapRange')
    roughness.inputs['From Max'].default_value = .65
    roughness.inputs['To Min'].default_value = .95
    roughness.inputs['To Max'].default_value = .65
    links.new(height.outputs['Color'], roughness.inputs['Value'])
    links.new(roughness.outputs['Result'], bsdf.inputs['Roughness'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--stamp', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    package = args.package.resolve()
    bpy.ops.wm.open_mainfile(filepath=str(package/'source/master.blend'))
    terrain = bpy.data.objects['Terrain']
    apply_texture(terrain, args.stamp)
    manifest = json.loads((package/'manifest.json').read_text())
    set_camera(manifest, 'close')
    scene = bpy.context.scene
    scene.cycles.samples = 48
    scene.render.filepath = str(package/'review/textured-close.png')
    bpy.ops.render.render(write_still=True)
    # A second crop demonstrates surface detail at closer range.
    pose = manifest['cameras']['close']
    pose['distance'] = 480; pose['pitch_deg'] = 36
    set_camera(manifest, 'close')
    scene.render.filepath = str(package/'review/textured-detail.png')
    bpy.ops.render.render(write_still=True)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(package/'source/textured-draft.blend'))


if __name__ == '__main__':
    main()
