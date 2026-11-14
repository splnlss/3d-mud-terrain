/** Khronos-validate the portable Colorado crown GLB and record the report beside it. */
import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import validator from 'gltf-validator';

const root = resolve(process.argv[2] ?? 'data/colorado-globe');
const path = resolve(root, 'colorado-crown.glb');
const report = await validator.validateBytes(new Uint8Array(await readFile(path)), { uri: 'colorado-crown.glb' });
await writeFile(resolve(root, 'gltf-validation.json'), JSON.stringify(report, null, 2) + '\n');
const { numErrors, numWarnings } = report.issues;
console.log(JSON.stringify({ path, numErrors, numWarnings, materials: report.info.materialCount, vertices: report.info.totalVertexCount, bytes: report.info.resources?.[0]?.byteLength }));
if (numErrors) { console.error(report.issues.messages.filter(m => m.severity === 0)); process.exitCode = 1; }
