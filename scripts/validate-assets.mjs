/** Validate every referenced GLB, implicit availability, and decoded tile bounds. */
import assert from 'node:assert/strict';
import { readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { getBounds } from '@gltf-transform/functions';
import { MeshoptDecoder } from 'meshoptimizer';
import { validateBytes } from 'gltf-validator';

const directory = process.argv[2] ?? 'public/terrain';
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });
const tileset = JSON.parse(await readFile(join(directory, 'tileset.json'), 'utf8'));
const manifest = JSON.parse(await readFile(join(directory, 'manifest.json'), 'utf8'));
assert.equal(tileset.asset.version, '1.1');
const root = tileset.root;
const levels = root.implicitTiling?.availableLevels ?? 1;
const errors = [], warnings = new Map();
let tiles = 0, waterTiles = 0, totalBytes = 0;
if (root.implicitTiling) {
  assert.equal(root.implicitTiling.subdivisionScheme, 'QUADTREE');
  const subtree = await readFile(join(directory, 'subtrees/0/0/0.subtree'));
  assert.equal(subtree.subarray(0,4).toString(), 'subt');
  assert.equal(subtree.readUInt32LE(4), 1);
  const length = Number(subtree.readBigUInt64LE(8));
  assert.equal(subtree.length, 24+length+Number(subtree.readBigUInt64LE(16)));
  const availability = JSON.parse(subtree.subarray(24,24+length));
  assert.equal(availability.tileAvailability.constant, 1);
  assert.equal(availability.contentAvailability[0].constant, 1);
  assert.equal(availability.childSubtreeAvailability.constant, 0);
}
for (let level=0; level<levels; level++) {
  const count = 2**level, span = manifest.size_m/count;
  for (let x=0; x<count; x++) for (let y=0; y<count; y++) {
    const uri = root.implicitTiling ? `tiles/${level}/${x}/${y}.glb` : root.content.uri;
    const path = join(directory, uri);
    const raw = await readFile(path);
    totalBytes += raw.length;
    const doc = await io.readBinary(raw);
    const scene = doc.getRoot().getDefaultScene();
    assert.ok(scene, `${uri}: no scene`);
    const bounds = getBounds(scene);
    const west = -manifest.size_m/2+x*span;
    const south = -manifest.size_m/2+y*span;
    // glTF x=east, z=south. Quantization may shift an edge by one quantization step.
    const tolerance = span/32767+.05;
    assert.ok(bounds.min[0]>=west-tolerance && bounds.max[0]<=west+span+tolerance, `${uri}: east/west bounds`);
    assert.ok(bounds.min[2]>=-south-span-tolerance && bounds.max[2]<=-south+tolerance, `${uri}: north/south bounds`);
    const zCenter = root.boundingVolume.box[2], zHalf = root.boundingVolume.box[11];
    assert.ok(bounds.min[1]>=zCenter-zHalf-tolerance && bounds.max[1]<=zCenter+zHalf+tolerance, `${uri}: vertical bounds`);
    if (doc.getRoot().listMaterials().some(material => material.getName()==='painted-water')) waterTiles++;
    for (const mesh of doc.getRoot().listMeshes()) for (const primitive of mesh.listPrimitives()) {
      if (primitive.getMaterial()?.getName()==='terrain') assert.ok(primitive.getAttribute('NORMAL'), `${uri}: terrain normals missing`);
    }
    // The Khronos validator does not decode EXT_meshopt_compression. Validate the
    // decoded equivalent after NodeIO has already verified/decompressed its buffers.
    doc.getRoot().listExtensionsUsed().find(extension => extension.extensionName===EXTMeshoptCompression.EXTENSION_NAME)?.dispose();
    const decoded = await io.writeBinary(doc);
    const result = await validateBytes(decoded, { uri, maxIssues: 30 });
    for (const issue of result.issues.messages) {
      if (issue.severity===0) errors.push({ uri, ...issue });
      else if (issue.severity===1) warnings.set(issue.code, (warnings.get(issue.code)??0)+1);
    }
    tiles++;
  }
}
const report = { tiles, waterTiles, totalBytes, errors, warningCounts: Object.fromEntries(warnings),
  note: 'Khronos glTF validation plus local implicit-quadtree availability and decoded bounds checks.' };
await writeFile('data/asset-validation.json', JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
assert.equal(errors.length, 0, 'GLB validation errors');
