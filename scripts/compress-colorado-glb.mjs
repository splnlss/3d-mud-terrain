/** Web copy of the Colorado crown: meshopt + KHR_mesh_quantization, unused UVs removed.
 *  The uncompressed colorado-crown.glb stays the portable asset (Blender and other tools). */
import { stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { meshopt } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';

await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder });
const root = resolve(process.argv[2] ?? 'data/colorado-globe');
const source = resolve(root, 'colorado-crown.glb'), target = resolve(root, 'colorado-crown-web.glb');
const doc = await io.read(source);
for (const mesh of doc.getRoot().listMeshes()) for (const primitive of mesh.listPrimitives()) {
  const uv = primitive.getAttribute('TEXCOORD_0'); if (uv) { primitive.setAttribute('TEXCOORD_0', null); if (!uv.listParents().some(p => p !== doc.getRoot())) uv.dispose(); }
}
await doc.transform(meshopt({ encoder: MeshoptEncoder, level: 'medium', quantizePosition: 16, quantizeNormal: 10, quantizeColor: 12 }));
await io.write(target, doc);
const before = (await stat(source)).size, after = (await stat(target)).size;
console.log(JSON.stringify({ target, portable_mb: +(before / 2 ** 20).toFixed(1), web_mb: +(after / 2 ** 20).toFixed(1) }));
