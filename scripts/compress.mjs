// Offline geometry compression; the browser only needs the meshopt decoder.
import { readdir } from 'node:fs/promises';
import { join } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { meshopt } from '@gltf-transform/functions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';

await Promise.all([MeshoptEncoder.ready, MeshoptDecoder.ready]);
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'meshopt.encoder': MeshoptEncoder, 'meshopt.decoder': MeshoptDecoder,
});
const root = process.argv[2] ?? 'public/terrain';
let count = 0;
async function compressDirectory(dir) {
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await compressDirectory(path);
    else if (entry.name.endsWith('.glb')) {
      const doc = await io.read(path);
      await doc.transform(meshopt({ encoder: MeshoptEncoder, level: 'medium',
        quantizePosition: 16, quantizeTexcoord: 16 }));
      await io.write(path, doc);
      count++;
    }
  }
}
await compressDirectory(root);
console.log(`Compressed ${count} GLBs with meshopt + KHR_mesh_quantization.`);
