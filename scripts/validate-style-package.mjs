/** Inspect the portable package without any preview-engine imports. */
import {readFile,realpath} from 'node:fs/promises';
import {resolve,relative,isAbsolute} from 'node:path';
import {NodeIO} from '@gltf-transform/core';
import validator from 'gltf-validator';

export async function validateStylePackage(root) {
  root=await realpath(root);
  const manifest=JSON.parse(await readFile(resolve(root,'manifest.json'),'utf8'));
  const errors=[];
  for(const file of manifest.files ?? []) {
    if(typeof file!=='string'||isAbsolute(file)||file.split(/[\\/]/).includes('..')||file.includes(':'))
      throw new Error('relative file path must not escape package');
    const path=await realpath(resolve(root,file));
    if(relative(root,path).startsWith('..')) throw new Error('file symlink escape');
  }
  const io=new NodeIO();let meshes=0,primitives=0;
  for(const lod of manifest.lods ?? []) {
    if(!manifest.files.includes(lod.path))throw new Error('LOD mesh not declared in files');
    const path=resolve(root,lod.path), bytes=new Uint8Array(await readFile(path));
    const report=await validator.validateBytes(bytes,{uri:lod.path});
    if(report.issues.numErrors) errors.push(`${lod.path}: ${report.issues.numErrors} glTF errors`);
    const doc=await io.read(path);meshes++;
    for(const node of doc.getRoot().listNodes())for(const primitive of node.getMesh()?.listPrimitives() ?? []) {
      const transform=node.getWorldMatrix();
      primitives++;
      const material=primitive.getMaterial();
      if(!material)errors.push('missing standard material');
      if(material?.getNormalTexture()) {
        const tangent=primitive.getAttribute('TANGENT');
        if(!tangent||tangent.getType()!=='VEC4')errors.push('missing TANGENT VEC4 for normal-mapped primitive');
        else {const array=tangent.getArray();for(let i=0;i<array.length;i+=4){
          if(!Number.isFinite(array[i])||Math.abs(Math.hypot(...array.slice(i,i+3))-1)>.005||Math.abs(Math.abs(array[i+3])-1)>1e-5){errors.push('invalid tangent orientation');break;}
        }}
      }
      const position=primitive.getAttribute('POSITION');
      if(!position)errors.push('missing positions');
      else if(lod.bounds_m) {
        const positions=position.getArray();const [min,max]=lod.bounds_m;
        let outside=false;
        for(let i=0;i<positions.length&&!outside;i+=3){
          const x=positions[i],y=positions[i+1],z=positions[i+2];
          for(let axis=0;axis<3;axis++){
            const world=transform[axis]*x+transform[axis+4]*y+transform[axis+8]*z+transform[axis+12];
            if(!Number.isFinite(world)||world<min[axis]-.05||world>max[axis]+.05){outside=true;break;}
          }
        }
        if(outside)errors.push('vertex outside declared bounds');
      }
    }
  }
  if(errors.length)throw new Error(errors.join('\n'));
  return {meshes,primitives,errors};
}
if(process.argv[1]?.endsWith('validate-style-package.mjs')) {
  try{console.log(JSON.stringify(await validateStylePackage(process.argv[2])));}
  catch(error){console.error(error.message);process.exitCode=1;}
}
