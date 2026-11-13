import { ADDRESS_CLAMP_TO_EDGE, ADDRESS_REPEAT, SEMANTIC_COLOR, SEMANTIC_NORMAL,
  SEMANTIC_POSITION, SEMANTIC_TEXCOORD0, ShaderMaterial, basisInitialize } from 'playcanvas';
import { loadTexture } from './texture-load';
import type { Application, Texture } from 'playcanvas';
import vertex from './shaders/terrain.vert?raw';
import fragment from './shaders/terrain.frag?raw';
import waterVertex from './shaders/water.vert?raw';
import waterFragment from './shaders/water.frag?raw';

export function initializeTextureDecoder() {
  const root = `${import.meta.env.BASE_URL}wasm/basis/`;
  basisInitialize({ glueUrl: root+'basis.wasm.js', wasmUrl: root+'basis.wasm.wasm',
    fallbackUrl: root+'basis.js', numWorkers: 1 });
}


export async function terrainMaterials(app: Application, size: number, direction = [.6,.45,.55]) {
  initializeTextureDecoder();
  const names = ['crust-albedo', 'crust-normal', 'granular-albedo', 'granular-normal'];
  const assets = await Promise.all(names.map(name => loadTexture(app.assets,
    `${import.meta.env.BASE_URL}terrain/detail/${name}.ktx2`)));
  const detail = assets.map(asset => asset.resource as Texture);
  const sun = direction.map(value=>value/Math.hypot(...direction));
  for (const texture of detail) texture.addressU = texture.addressV = ADDRESS_REPEAT;
  const water = new ShaderMaterial({ uniqueName: 'painted-water', vertexGLSL: waterVertex,
    fragmentGLSL: waterFragment, attributes: { aPosition: SEMANTIC_POSITION } });
  water.name = 'painted-water';
  water.setParameter('uNormal', detail[3]);
  water.setParameter('uSun', sun);
  water.setParameter('uShoreMap', detail[0]);
  water.setParameter('uBounds', [-size/2,size/2,size,size]);
  water.setParameter('uTime', 0);
  water.setParameter('uLevel', 0);
  water.setParameter('uEye', [0,1,0]);
  water.setParameter('uExtent', size);
  const terrain = (mask: Texture) => {
    mask.addressU = mask.addressV = ADDRESS_CLAMP_TO_EDGE;
    const material = new ShaderMaterial({
      uniqueName: 'relief-pfyffer-terrain', vertexGLSL: vertex, fragmentGLSL: fragment,
      attributes: { aPosition: SEMANTIC_POSITION, aNormal: SEMANTIC_NORMAL,
        aColor: SEMANTIC_COLOR, aUv: SEMANTIC_TEXCOORD0 },
    });
    material.setParameter('uMask', mask);
    for (const [index, name] of ['uCrustAlbedo', 'uCrustNormal', 'uGranularAlbedo', 'uGranularNormal'].entries()) {
      material.setParameter(name, detail[index]);
    }
    material.setParameter('uWetness', .35);
    material.setParameter('uExtent', size);
    material.setParameter('uSun', sun);
    return material;
  };
  return { terrain, water };
}
