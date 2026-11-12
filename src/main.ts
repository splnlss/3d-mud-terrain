import {
  Application, Color, Entity, StandardMaterial, createGraphicsDevice,
  DEVICETYPE_WEBGL2, FILLMODE_FILL_WINDOW, RESOLUTION_AUTO, TONEMAP_ACES,
  meshoptInitialize, Quat, Vec3,
} from 'playcanvas';
import type { RenderComponent, Asset, ShaderMaterial, Texture } from 'playcanvas';
import { MeshoptDecoder } from 'meshoptimizer';
import { TilesRenderer } from '3d-tiles-renderer/playcanvas';
import { ImplicitTilingPlugin } from '3d-tiles-renderer/core/plugins';
import { Orbit } from './orbit';
import { terrainMaterials } from './materials';
import { loadTexture } from './texture-load';
import { materialRole } from './material-role';
import { FrameTrace } from './trace';
import './style.css';

const canvas = document.querySelector<HTMLCanvasElement>('#terrain')!;
const status = document.querySelector<HTMLDivElement>('#status')!;
const metrics = document.querySelector<HTMLOutputElement>('#metrics')!;

function showRetry(message: string) {
  status.replaceChildren(document.createTextNode(message+' '));
  const button=document.createElement('button');
  button.type='button';
  button.textContent='Retry view';
  button.addEventListener('click',()=>location.reload());
  status.appendChild(button);
  status.hidden=false;
}
const startupHelp=setTimeout(()=>{
  if (!status.hidden) showRetry('Loading is taking longer than expected. Keep waiting or retry.');
},30000);


async function start() {
  const response = await fetch(`${import.meta.env.BASE_URL}terrain/manifest.json`);
  if (!response.ok) throw new Error('Terrain data is not available. Please try again later.');
  const manifest = await response.json();
  const size: number = manifest.size_m;
  document.querySelector('#diagnostics p')!.textContent = 'San Luis elevation study';
  document.querySelectorAll('#diagnostics p')[1].textContent = `PlayCanvas · USGS 3DEP · ${manifest.spacing_m} m · ${size/1000} × ${size/1000} km · ${manifest.material ? 'Pfyffer material study' : 'Diagnostic material'}`;
  await MeshoptDecoder.ready;
  meshoptInitialize({ decoder: MeshoptDecoder });
  const device = await createGraphicsDevice(canvas, {
    deviceTypes: [DEVICETYPE_WEBGL2], antialias: window.devicePixelRatio<2,
    powerPreference: 'high-performance',
  });
  canvas.dataset.boot = 'device';
  const app = new Application(canvas, { graphicsDevice: device });
  canvas.dataset.boot = 'application';
  app.graphicsDevice.maxPixelRatio = window.devicePixelRatio;
  app.setCanvasFillMode(FILLMODE_FILL_WINDOW);
  app.setCanvasResolution(RESOLUTION_AUTO);
  const gl = canvas.getContext('webgl2')!;
  const samples = Math.max(1, Number(gl.getParameter(gl.SAMPLES)));
  const rendererInfo = gl.getExtension('WEBGL_debug_renderer_info');
  const renderer = gl.getParameter(rendererInfo?.UNMASKED_RENDERER_WEBGL ?? gl.RENDERER);
  canvas.dataset.renderer = String(renderer);
  function gpuBytes() {
    const vram = app.stats.vram;
    // Browser-owned default framebuffer is outside PlayCanvas' allocation counters.
    const framebuffer = canvas.width*canvas.height*(8*samples+(samples>1 ? 4 : 0));
    return vram.tex+vram.vb+vram.ib+vram.ub+vram.sb+framebuffer;
  }
  app.scene.ambientLight = new Color(.55, .51, .44);
  const sunDirection: number[] = manifest.lighting?.sun_direction ?? [.6,.45,.55];
  const style = manifest.material ? await terrainMaterials(app, size, sunDirection) : null;
  type TileMaterial = { asset?: Asset; material?: ShaderMaterial; water?: ShaderMaterial; timer?: ReturnType<typeof setTimeout> };
  const customTiles = new Map<Entity, TileMaterial>();
  const camera = new Entity('camera');
  camera.addComponent('camera', {
    clearColor: new Color(0xe5/255, 0xdf/255, 0xd3/255),
    fov: 38, nearClip: size/10000, farClip: size*8, toneMapping: TONEMAP_ACES,
  });
  app.root.addChild(camera);
  const sun = new Entity('warm-low-sun');
  sun.addComponent('light', { type: 'directional', color: new Color(1, .88, .7),
    intensity: 1.6, castShadows: false });
  sun.setRotation(new Quat().setFromDirections(Vec3.UP,
    new Vec3(sunDirection[0],sunDirection[1],sunDirection[2]).normalize()));
  app.root.addChild(sun);
  const material = new StandardMaterial();
  material.diffuse = new Color(.64, .54, .4);
  material.gloss = 0;
  material.useMetalness = true;
  material.metalness = 0;
  material.update();
  const tiles = new TilesRenderer(`${import.meta.env.BASE_URL}terrain/tileset.json`, app);
  tiles.registerPlugin(new ImplicitTilingPlugin());
  tiles.setCamera(camera.camera!);
  tiles.group.setEulerAngles(-90, 0, 0);
  tiles.errorTarget = 8;
  tiles.lruCache.maxBytesSize = 80*1024*1024;
  tiles.lruCache.minBytesSize = 50*1024*1024;
  tiles.lruCache.maxSize = 128;
  tiles.lruCache.minSize = 64;
  tiles.renderOptions = { castShadows: false, receiveShadows: false };
  app.root.addChild(tiles.group);
  const readyTiles=new Set<Entity>(), failedTiles=new Set<Entity>(), slowTiles=new Set<Entity>();
  const failedUrls=new Set<string>();
  function refreshStatus() {
    if (failedTiles.size || failedUrls.size) showRetry('Some terrain could not load. Check your connection and retry.');
    else if (slowTiles.size) showRetry('Some detail is taking longer to load. Keep waiting or retry.');
    else if (readyTiles.size) status.hidden=true;
  }
  tiles.on('load-model', async ({ scene, url }) => {
    for (const render of scene.findComponents('render') as RenderComponent[]) {
      for (const instance of render.meshInstances) {
        instance.material = materialRole(instance.material?.name) === 'water' && style ? style.water : material;
      }
    }
    if (style) {
      const record: TileMaterial = {};
      customTiles.set(scene, record);
      record.timer=setTimeout(()=>{
        if (customTiles.get(scene)===record) { slowTiles.add(scene);refreshStatus(); }
      },30000);
      try {
        const match = new URL(url, location.href).pathname.match(/tiles\/(\d+)\/(\d+)\/(\d+)\.glb$/);
        if (!match) throw new Error('Terrain tile URL does not match the bake layout');
        const asset = await loadTexture(app.assets, `${import.meta.env.BASE_URL}terrain/masks/${match[1]}/${match[2]}/${match[3]}.ktx2`);
        if (!customTiles.has(scene)) {
          asset.unload();
          app.assets.remove(asset);
          return;
        }
        record.asset = asset;
        record.material = style.terrain(asset.resource as Texture);
        record.material.setParameter('uWetness', wetness);
        record.water = style.water.clone();
        record.water.setParameter('uShoreMap', asset.resource as Texture);
        const span = size/2**Number(match[1]);
        record.water.setParameter('uBounds', [-size/2+Number(match[2])*span,
          -size/2+(Number(match[3])+1)*span, span, span]);
        for (const render of scene.findComponents('render') as RenderComponent[]) {
          for (const instance of render.meshInstances) {
            instance.material = instance.material === style.water ? record.water : record.material;
          }
        }
      } catch (error) {
        if (customTiles.has(scene)) { console.error(error);failedTiles.add(scene); }
        return;
      } finally {
        clearTimeout(record.timer);
        slowTiles.delete(scene);
        refreshStatus();
      }
    }
    readyTiles.add(scene);
    failedTiles.delete(scene);
    failedUrls.delete(url);
    clearTimeout(startupHelp);
    refreshStatus();
  });
  tiles.on('dispose-model', ({ scene }) => {
    const record = customTiles.get(scene);
    customTiles.delete(scene);
    readyTiles.delete(scene);failedTiles.delete(scene);slowTiles.delete(scene);
    clearTimeout(record?.timer);
    refreshStatus();
    record?.material?.destroy();
    record?.water?.destroy();
    if (record?.asset) {
      record.asset.unload();
      app.assets.remove(record.asset);
    }
  });
  tiles.on('load-error', ({url}) => {
    failedUrls.add(String(url));
    refreshStatus();
  });
  const centerHeight = Math.max(0, manifest.mesh.height_range_m[1]*.2);
  const preview: number[][] | undefined = manifest.preview_heights_m;
  function groundHeight(x: number, z: number, clearance = false) {
    if (!preview) return centerHeight;
    const n = preview.length;
    const row = Math.round((.5+z/size)*(n-1));
    const col = Math.round((.5+x/size)*(n-1));
    if (!clearance) return preview[Math.max(0,Math.min(n-1,row))][Math.max(0,Math.min(n-1,col))];
    // A neighbourhood maximum gives the camera clearance above unresolved ridges.
    let maximum = 0;
    for (let dy=-1; dy<=1; dy++) for (let dx=-1; dx<=1; dx++) {
      maximum = Math.max(maximum, preview[Math.max(0, Math.min(n-1,row+dy))][Math.max(0, Math.min(n-1,col+dx))]);
    }
    return maximum;
  }
  let wetness = .35, waterLevel = 0;
  const notes = document.querySelector('#diagnostics')!;
  if (style) {
    const controls = document.createElement('div');
    controls.innerHTML = `<label>Wetness <input id="wetness" aria-label="Wetness" type="range" min="0" max="1" step="0.01" value="0.35"></label>
      ${manifest.water ? '<label>Water level <input id="water-level" aria-label="Water level" type="range" min="-1" max="1" step="0.05" value="0"></label>' : ''}
      <p>Height curve: ${manifest.style.gain}× / ${manifest.style.knee_m} m knee<br>Curve changes require a rebake.</p>`;
    notes.appendChild(controls);
    document.querySelector<HTMLInputElement>('#wetness')!.addEventListener('input', event => {
      wetness = Number((event.target as HTMLInputElement).value);
      for (const record of customTiles.values()) record.material?.setParameter('uWetness', wetness);
    });
    document.querySelector<HTMLInputElement>('#water-level')?.addEventListener('input', event => {
      waterLevel = Number((event.target as HTMLInputElement).value);
      style.water.setParameter('uLevel', waterLevel);
      for (const record of customTiles.values()) record.water?.setParameter('uLevel', waterLevel);
    });
  }
  let trace: FrameTrace | null = null;
  let traceStarted = 0;
  const traceButton = document.createElement('button');
  traceButton.textContent = 'Record 60-second trace';
  const traceStatus = document.createElement('output');
  traceStatus.setAttribute('aria-live', 'polite');
  notes.append(traceButton, traceStatus);
  traceButton.addEventListener('click', () => {
    trace = new FrameTrace();
    traceStarted = performance.now();
    traceButton.disabled = true;
    traceStatus.textContent = 'Orbit, pan and zoom while recording.';
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) trace?.invalidate('Page was hidden during capture');
  });
  canvas.addEventListener('webglcontextlost', () => trace?.invalidate('WebGL context was lost'));
  let orbit = new Orbit(size, centerHeight, innerWidth/innerHeight);
  document.querySelector('#reset')!.addEventListener('click', () => { orbit = new Orbit(size, centerHeight, innerWidth/innerHeight); });
  if (manifest.views) {
    const select = document.createElement('select');
    select.setAttribute('aria-label', 'Fixed camera view');
    select.id = 'view-preset';
    select.add(new Option('Overview', ''));
    for (const name of Object.keys(manifest.views)) select.add(new Option(name, name));
    select.addEventListener('change', () => {
      orbit = new Orbit(size, centerHeight, innerWidth/innerHeight);
      if (select.value) {
        const view = manifest.views[select.value];
        orbit.x = view.x;
        orbit.z = view.z;
        orbit.distance = view.distance;
      }
    });
    notes.querySelector('summary')!.after(select);
    document.querySelector('#reset')!.addEventListener('click', () => { select.value = ''; });
  }
  canvas.tabIndex = 0;
  canvas.addEventListener('keydown', event => {
    const direction: Record<string, [number,number]> = { ArrowLeft: [-25,0], ArrowRight: [25,0], ArrowUp: [0,-25], ArrowDown: [0,25] };
    if (direction[event.key]) {
      const [dx,dy] = direction[event.key];
      if (event.shiftKey) orbit.pan(dx,dy);
      else orbit.rotate(dx,dy);
    } else if (event.key==='+' || event.key==='=') orbit.zoom(-160);
    else if (event.key==='-') orbit.zoom(160);
    else if (event.key==='Home') document.querySelector<HTMLButtonElement>('#reset')!.click();
    else return;
    event.preventDefault();
  });
  const pointers = new Map<number, { x: number; y: number }>();
  canvas.addEventListener('contextmenu', event => event.preventDefault());
  canvas.addEventListener('pointerdown', event => {
    canvas.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  });
  canvas.addEventListener('pointermove', event => {
    const previous = pointers.get(event.pointerId);
    if (!previous) return;
    const dx = event.clientX-previous.x, dy = event.clientY-previous.y;
    if (pointers.size === 2) {
      const other = [...pointers.entries()].find(([id]) => id!==event.pointerId)![1];
      const before = Math.hypot(previous.x-other.x, previous.y-other.y);
      const after = Math.hypot(event.clientX-other.x, event.clientY-other.y);
      if (after>0 && before>0) orbit.zoom(Math.log(before/after)*1000);
      orbit.pan(dx*.5, dy*.5);
    } else if (event.buttons === 2 || event.shiftKey) orbit.pan(dx, dy);
    else orbit.rotate(dx, dy);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  });
  for (const name of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    canvas.addEventListener(name, event => { pointers.delete((event as PointerEvent).pointerId); });
  }
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    orbit.zoom(event.deltaY*(event.deltaMode===1 ? 16 : event.deltaMode===2 ? innerHeight : 1));
  }, { passive: false });
  window.addEventListener('resize', () => {
    app.resizeCanvas();
    orbit.resize(innerWidth/innerHeight);
  });
  let elapsed = 0, frames = 0, time = 0;
  app.on('update', (dt: number) => {
    orbit.height = groundHeight(orbit.x, orbit.z)+size*.002;
    const eye = orbit.eye;
    eye[1] = Math.max(eye[1], groundHeight(eye[0], eye[2], true)+size*.003);
    camera.setPosition(...eye);
    camera.lookAt(orbit.x, orbit.height, orbit.z);
    camera.camera!.nearClip = Math.max(.01,orbit.distance*.01);
    camera.camera!.farClip = orbit.distance+size*2;
    if (style) {
      time += dt;
      style.water.setParameter('uTime', time);
      style.water.setParameter('uEye', eye);
      for (const record of customTiles.values()) if (record.water) {
        record.water.setParameter('uTime', time);
        record.water.setParameter('uEye', eye);
      }
    }
    tiles.update();
    if (trace) {
      const result = trace.add(performance.now(), app.stats.drawCalls.total, gpuBytes());
      if (result) {
        const report = { ...result, capturedAt: new Date().toISOString(),
          browser: navigator.userAgent, renderer, viewport: [innerWidth, innerHeight, devicePixelRatio],
          renderResolution: [canvas.width, canvas.height], antialiasSamples: samples,
          gpuEstimate: 'PlayCanvas allocations plus estimated browser framebuffer; excludes driver overhead',
          budgetsPass: result.valid && result.fps>=60 && result.within16_7Percent>=95 &&
            result.peakDraws<=200 && result.peakGpuBytes<150000000,
          bake: { sources: manifest.sources, style: manifest.style, mesh: manifest.mesh,
            lighting: manifest.lighting, material: manifest.material, toolchain: manifest.toolchain } };
        canvas.dataset.trace = JSON.stringify(report);
        const link = document.createElement('a');
        const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
        link.href = objectUrl;
        link.download = 'san-luis-performance.json';
        link.click();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        traceStatus.textContent = `${result.fps.toFixed(1)} fps · p95 ${result.p95Ms.toFixed(1)} ms · ${report.budgetsPass ? 'passes' : 'does not pass'} trace budgets`;
        traceButton.disabled = false;
        traceButton.textContent = 'Record 60-second trace';
        trace = null;
      }
    }
    elapsed += dt;
    frames++;
    if (elapsed>1) {
      metrics.value = `${Math.round(frames/elapsed)} fps · ${app.stats.drawCalls.total} draws · ${readyTiles.size} tiles loaded`;
      canvas.dataset.loaded = String(readyTiles.size);
      canvas.dataset.draws = String(app.stats.drawCalls.total);
      canvas.dataset.camera = JSON.stringify(eye);
      canvas.dataset.engine = 'PlayCanvas';
      canvas.dataset.gpuBytes = String(gpuBytes());
      if (trace) traceButton.textContent = `Recording · ${Math.max(0, Math.ceil(60-(performance.now()-traceStarted)/1000))} s`;
      elapsed = frames = 0;
    }
  });
  app.start();
  canvas.dataset.boot = 'started';
  canvas.dataset.contextLost = String(app.graphicsDevice.contextLost);
  if (import.meta.env.DEV) Object.assign(window, { reliefApp: app });
}

start().catch((error: Error) => {
  console.error(error);
  clearTimeout(startupHelp);
  showRetry(error.message.includes('Terrain data') ? error.message : 'The terrain view could not start. Check your connection or browser and retry.');
});
