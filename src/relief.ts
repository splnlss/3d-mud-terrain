/** Preview adapter for the geo-registered relief tileset (public/relief/tileset.json). */
import { ADDRESS_REPEAT, Application, Color, DETAILMODE_OVERLAY, Entity, Mesh, MeshInstance, StandardMaterial as Standard, FILLMODE_FILL_WINDOW, Mat4, Quat, RESOLUTION_AUTO, Vec3, basisInitialize, createGraphicsDevice, dracoInitialize, TONEMAP_ACES, TONEMAP_NONE, Vec2 } from 'playcanvas';
import type { Asset, RenderComponent, StandardMaterial, Texture } from 'playcanvas';
import { TilesRenderer } from '3d-tiles-renderer/playcanvas';
import { GoogleCloudAuthPlugin } from '3d-tiles-renderer/core/plugins';
import { Orbit } from './orbit';

const canvas = document.querySelector<HTMLCanvasElement>('#terrain')!;
const info = document.querySelector<HTMLDivElement>('#info')!;
const query = new URLSearchParams(location.search);
const set = query.get('set') ?? 'relief-sample';
// 'google' shows Google Photorealistic 3D Tiles in the same frame, for comparison. It still reads a relief
// tileset for the region frame. The key comes from the dev server's environment and is never stored in the repo.
const google = set === 'google';
const googleKey = import.meta.env.VITE_GOOGLE_MAPS_KEY as string | undefined;
// A deployed build reads the tiles from remote storage (VITE_RELIEF_BASE is the published folder of one tileset);
// the dev server reads the local sets linked under public/.
const remote = import.meta.env.VITE_RELIEF_BASE as string | undefined;
const folder = remote ? `${remote.replace(/\/$/, '')}/` : `${import.meta.env.BASE_URL}${google ? 'relief-sample' : set}/`;
const url = `${folder}tileset.json`;
const SETS: Record<string, string> = remote ? { 'relief-sample': 'San Luis sample (×1.25, walkable)' }
  : { 'relief-sample': 'San Luis sample (×1.25, walkable)', 'relief-v2': 'Previous relief (mixed scale)', google: 'Google 3D Tiles (true scale)' };
const optional = async (file: string) => { try { const r = await fetch(folder + file); return r.ok ? r : null; } catch { return null; } };

async function main() {
  const tileset = await (await fetch(url)).json();
  const wasm = `${import.meta.env.BASE_URL}wasm/basis/`;
  basisInitialize({ glueUrl: wasm+'basis.wasm.js', wasmUrl: wasm+'basis.wasm.wasm', fallbackUrl: wasm+'basis.js', numWorkers: 2 });
  const draco = `${import.meta.env.BASE_URL}wasm/draco/`;
  if (google) dracoInitialize({ jsUrl: draco+'draco.wasm.js', wasmUrl: draco+'draco.wasm.wasm', numWorkers: 2, lazyInit: false });
  const device = await createGraphicsDevice(canvas, { deviceTypes: ['webgl2'], antialias: true });
  const app = new Application(canvas, { graphicsDevice: device });
  app.graphicsDevice.maxPixelRatio = Math.min(devicePixelRatio, 2);
  app.setCanvasFillMode(FILLMODE_FILL_WINDOW);
  app.setCanvasResolution(RESOLUTION_AUTO);
  app.start();

  // The tileset is in Earth-centred coordinates. Its root transform gives the east/north/up frame at the
  // region centre; the group undoes it so the region sits at the origin with +Y up and north toward -Z.
  const t: number[] = tileset.root.transform;
  const east = [t[0], t[1], t[2]], north = [t[4], t[5], t[6]], up = [t[8], t[9], t[10]], centre = [t[12], t[13], t[14]];
  const dot = (a: number[], b: number[]) => a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
  const frame = new Mat4().set([
    east[0], up[0], -north[0], 0, east[1], up[1], -north[1], 0, east[2], up[2], -north[2], 0,
    -dot(east, centre), -dot(up, centre), dot(north, centre), 1]);
  const [west, south, eastEdge, northEdge] = tileset.root.extras.region_radians_metres;
  const size = 6371000 * (northEdge - south);
  const scale = 1 / 1000;  // kilometres keep single-precision positions stable

  const camera = new Entity('camera');
  camera.addComponent('camera', { clearColor: new Color(.9, .87, .83), fov: 38, nearClip: size*scale/5000, farClip: size*scale*8, toneMapping: google ? TONEMAP_NONE : TONEMAP_ACES });  // Google's textures are finished photographs; the clay is lit and needs the curve
  app.root.addChild(camera);
  const sun = new Entity('warm-low-sun');
  sun.addComponent('light', { type: 'directional', color: new Color(1, .86, .68), intensity: 1.7, castShadows: false });
  sun.setEulerAngles(58, 215, 0);
  app.root.addChild(sun);
  app.scene.ambientLight = new Color(.5, .46, .42);
  // Google's tiles are unlit photographs that already contain sunlight and shadow; any scene light only adds haze.
  if (google) { sun.enabled = false; app.scene.ambientLight = new Color(0, 0, 0); }

  if (google && !googleKey) throw new Error('Google view needs the dev server started with the Maps key: see docs/relief-process.md');
  const tiles = google ? new TilesRenderer(undefined as never, app) : new TilesRenderer(url, app);
  if (google) tiles.registerPlugin(new GoogleCloudAuthPlugin({ apiToken: googleKey!, autoRefreshToken: true }));
  tiles.setCamera(camera.camera!);
  tiles.errorTarget = Number(query.get('error') ?? (google ? 20 : 6));
  const budget = Number(query.get('cacheMB') ?? 900)*1024*1024;
  tiles.lruCache.maxBytesSize = budget;
  tiles.lruCache.minBytesSize = budget*.7;
  const holder = new Entity('region frame');
  holder.setLocalScale(scale, scale, scale);
  holder.setLocalRotation(new Quat().setFromMat4(frame));
  holder.setLocalPosition(frame.getTranslation().mulScalar(scale));
  holder.addChild(tiles.group);
  app.root.addChild(holder);
  let loaded = 0, failed = 0, problem = '';
  // Close-range dirt detail: one repeating square of ground laid over every tile, so the surface stays
  // interesting within a few metres. Tile sides are exact multiples of its span, so it is continuous across tiles.
  const detailInfo = google ? null : await (await optional('detail/detail.json'))?.json() as { span_m: number } | undefined;
  const texture = (file: string, srgb: boolean) => new Promise<Texture | null>(resolve => app.assets.loadFromUrl(folder + file, 'texture', (error: unknown, asset?: Asset) => {
    const tex = error || !asset ? null : asset.resource as Texture;
    if (tex) { tex.addressU = tex.addressV = ADDRESS_REPEAT; tex.anisotropy = 8; tex.srgb = srgb; }
    resolve(tex);
  }));
  const detail = detailInfo && query.get('detail') !== '0' ? { normal: await texture('detail/dirt-normal.png', false), tone: await texture('detail/dirt-tone.png', true), span: detailInfo.span_m } : null;
  tiles.on('load-model', ({ scene, url: tileUrl }: { scene: Entity, url: string }) => {
    loaded++;
    const level = Number(/tiles\/(\d+)-/.exec(tileUrl)?.[1] ?? NaN);
    if (detail?.normal && detail.tone && !Number.isNaN(level)) {
      const repeats = 2 ** (14 - level), shift = -.5*repeats/1536;  // texture coordinates start half a texel inside the tile
      for (const render of scene.findComponents('render') as RenderComponent[]) for (const instance of render.meshInstances) {
        const material = instance.material as StandardMaterial;
        material.normalDetailMap = detail.normal; material.normalDetailMapTiling = new Vec2(repeats, repeats); material.normalDetailMapOffset = new Vec2(shift, shift);
        material.normalDetailMapBumpiness = 1.1;
        material.diffuseDetailMap = detail.tone; material.diffuseDetailMapTiling = new Vec2(repeats, repeats); material.diffuseDetailMapOffset = new Vec2(shift, shift);
        material.diffuseDetailMode = DETAILMODE_OVERLAY;
        material.update();
      }
    }
    if (query.has('debug')) setTimeout(() => {
      const render = scene.findComponents('render')[0] as unknown as { meshInstances: { aabb: { center: Vec3, halfExtents: Vec3 }, material: { name: string } }[] };
      const box = render?.meshInstances[0]?.aabb;
      problem = box ? `aabb ${box.center.toString()} ± ${box.halfExtents.toString()} cam ${camera.getPosition().toString()}` : 'no mesh';
    }, 500);
  });
  tiles.on('load-error', (event: { error?: unknown }) => { failed++; problem = String(event.error ?? ''); });
  addEventListener('error', event => { problem = event.message; });
  addEventListener('unhandledrejection', event => { problem = String(event.reason); });

  const orbit = new Orbit(size*scale, 0, canvas.clientWidth/Math.max(1, canvas.clientHeight));
  for (const key of ['yaw', 'pitch', 'distance', 'x', 'z'] as const) if (query.has(key)) orbit[key] = Number(query.get(key));
  canvas.addEventListener('contextmenu', event => event.preventDefault());
  // Ground heights let the camera come down to walking height and follow the terrain.
  const groundInfo = google ? null : await (await optional('ground.json'))?.json() as { size: number, cell_m: number, half_km: number } | undefined;
  const groundData = groundInfo ? new Uint16Array(await (await fetch(folder + 'ground.bin')).arrayBuffer()) : null;
  /** Terrain height in scene kilometres at scene x, z; null outside the mapped square. */
  const ground = (x: number, z: number) => {
    if (!groundInfo || !groundData) return null;
    const n = groundInfo.size, c = (x*1000 + groundInfo.half_km*1000)/groundInfo.cell_m, r = (z*1000 + groundInfo.half_km*1000)/groundInfo.cell_m;
    if (c < 0 || r < 0 || c >= n - 1 || r >= n - 1) return null;
    const c0 = Math.floor(c), r0 = Math.floor(r), fc = c - c0, fr = r - r0, at = (rr: number, cc: number) => groundData[rr*n + cc]/10;
    const metres = (at(r0, c0)*(1 - fc) + at(r0, c0 + 1)*fc)*(1 - fr) + (at(r0 + 1, c0)*(1 - fc) + at(r0 + 1, c0 + 1)*fc)*fr;
    return (metres - (x*x + z*z)*1e6/(2*6371000))/1000;  // the tileset frame is a flat tangent plane, so the round Earth drops away from its centre
  };
  const walkable = () => ground(orbit.x, orbit.z) !== null;
  canvas.addEventListener('pointermove', event => {
    if (!event.buttons) return;
    if (event.buttons === 2 || event.shiftKey) orbit.pan(event.movementX, event.movementY);
    else if (walkable()) { orbit.yaw -= event.movementX*.005; orbit.pitch = Math.max(.03, Math.min(1.45, orbit.pitch + event.movementY*.005)); }
    else orbit.rotate(event.movementX, event.movementY);
  });
  // The canvas follows the window, including when the page goes full screen.
  const fit = () => { app.resizeCanvas(); orbit.resize(innerWidth/Math.max(1, innerHeight)); };
  addEventListener('resize', fit);
  document.addEventListener('fullscreenchange', fit);
  const fullscreen = () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
  document.querySelector<HTMLButtonElement>('#fullscreen')!.addEventListener('click', fullscreen);
  addEventListener('keydown', event => { if (event.key === 'f' || event.key === 'F') fullscreen(); });
  // Every set opens at the same camera, so they can be compared from one viewpoint.
  const tools = document.querySelector<HTMLDivElement>('#sets')!;
  for (const [name, label] of Object.entries(SETS)) {
    const link = document.createElement('a'); link.textContent = label; link.href = '#';
    if (name === set) link.className = 'current';
    link.addEventListener('click', event => {
      event.preventDefault();
      const next = new URLSearchParams({ set: name, yaw: String(orbit.yaw), pitch: String(orbit.pitch), distance: String(orbit.distance), x: String(orbit.x), z: String(orbit.z) });
      location.search = next.toString();
    });
    tools.append(link);
  }
  // Irrigation ditches and acequias, draped on the ground map as ribbons. Toggle with the button or D.
  type Ditch = { geometry: { coordinates: number[][] }, properties: { acequia: boolean, name: string | null } };
  const ditchData = google ? null : await (await optional('ditches/ditches.geojson'))?.json() as { features: Ditch[] } | undefined;
  const ditchLayer = new Entity('ditches'); app.root.addChild(ditchLayer); ditchLayer.enabled = query.get('ditches') !== '0';
  const toScene = (lon: number, lat: number) => {  // WGS84 longitude/latitude to scene kilometres (x east, z south)
    const a = 6378137, e2 = 6.69437999014e-3, l = lon*Math.PI/180, p = lat*Math.PI/180, n = a/Math.sqrt(1 - e2*Math.sin(p)**2);
    const ecef = [n*Math.cos(p)*Math.cos(l), n*Math.cos(p)*Math.sin(l), n*(1 - e2)*Math.sin(p)];
    const d = [ecef[0] - centre[0], ecef[1] - centre[1], ecef[2] - centre[2]];
    return [dot(d, east)*scale, -dot(d, north)*scale];
  };
  const ditchLines = (ditchData?.features ?? []).map(f => ({ acequia: f.properties.acequia, points: f.geometry.coordinates.map(([lon, lat]) => toScene(lon, lat)) }));
  let ditchWidth = 0;
  const buildDitches = (width: number) => {
    ditchWidth = width; ditchLayer.children.slice().forEach(child => child.destroy());
    for (const acequia of [false, true]) {
      const positions: number[] = [], indices: number[] = [];
      for (const line of ditchLines.filter(l => l.acequia === acequia)) {
        const pts = line.points.map(([x, z]) => [x, z, ground(x, z)] as const).filter(p => p[2] !== null) as [number, number, number][];
        for (let i = 0; i + 1 < pts.length; i++) {
          const [x0, z0, y0] = pts[i], [x1, z1, y1] = pts[i + 1], len = Math.hypot(x1 - x0, z1 - z0) || 1;
          const w = (acequia ? 1.5 : 1)*width/2, nx = -(z1 - z0)/len*w, nz = (x1 - x0)/len*w, lift = .002 + width*.2, b = positions.length/3;
          positions.push(x0 + nx, y0 + lift, z0 + nz, x0 - nx, y0 + lift, z0 - nz, x1 + nx, y1 + lift, z1 + nz, x1 - nx, y1 + lift, z1 - nz);
          indices.push(b, b + 2, b + 1, b + 1, b + 2, b + 3);
        }
      }
      if (!positions.length) continue;
      const mesh = new Mesh(app.graphicsDevice); mesh.setPositions(positions); mesh.setIndices(indices); mesh.update();
      const material = new Standard(); material.useLighting = false; material.diffuse = new Color(0, 0, 0); material.cull = 0;
      material.emissive = acequia ? new Color(.85, .12, .1) : new Color(.1, .45, .95); material.update();
      const holder = new Entity(acequia ? 'acequias' : 'ditches'); holder.addComponent('render', { meshInstances: [new MeshInstance(mesh, material)] });
      ditchLayer.addChild(holder);
    }
  };
  const ditchButton = document.querySelector<HTMLButtonElement>('#ditches')!;
  ditchButton.hidden = !ditchLines.length;
  const showDitches = (on: boolean) => { ditchLayer.enabled = on; ditchButton.className = on ? 'current' : ''; };
  showDitches(ditchLayer.enabled);
  ditchButton.addEventListener('click', () => showDitches(!ditchLayer.enabled));
  addEventListener('keydown', event => { if (event.key === 'd' || event.key === 'D') showDitches(!ditchLayer.enabled); });
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    // Over the mapped square the camera may come within two metres of the ground.
    if (walkable()) orbit.distance = Math.max(.002, Math.min(orbit.maxDistance, orbit.distance*Math.exp(Math.max(-1, Math.min(1, event.deltaY*.001)))));
    else orbit.zoom(event.deltaY);
  }, { passive: false });
  app.on('update', () => {
    const here = ground(orbit.x, orbit.z);
    // The view target rides on the terrain once the camera is near it, and eases back to the base level far away.
    const near = Math.max(0, Math.min(1, (60 - orbit.distance)/40));
    orbit.height = here === null ? 0 : here*near;
    if (here === null && orbit.distance < size*scale*.015) orbit.distance = size*scale*.015;
    if (here === null) orbit.pitch = Math.max(.35, Math.min(1.2, orbit.pitch));
    const flat = Math.cos(orbit.pitch)*orbit.distance;
    const eye = new Vec3(orbit.x + Math.sin(orbit.yaw)*flat, orbit.height + Math.sin(orbit.pitch)*orbit.distance, orbit.z + Math.cos(orbit.yaw)*flat);
    const below = ground(eye.x, eye.z);
    if (below !== null) eye.y = Math.max(eye.y, below + .0017);  // never under the ground: eye height at least 1.7 m
    camera.setPosition(eye);
    camera.lookAt(new Vec3(orbit.x, orbit.height, orbit.z));
    // Ribbons stay readable at any distance: about 2 px wide, never narrower than 3 m on the ground.
    const width = Math.max(.003, orbit.distance*.0016);
    if (ditchLines.length && ditchLayer.enabled && (width > ditchWidth*1.6 || width < ditchWidth/1.6)) buildDitches(width);
    camera.camera!.nearClip = Math.max(.0003, orbit.distance/200);
    camera.camera!.farClip = Math.max(60, orbit.distance*40);
    tiles.update();
    info.textContent = `${loaded} tiles loaded${failed ? `, ${failed} failed` : ''}${problem ? ` · ${problem}` : ''}${google ? ' · Google 3D Tiles: ' + (tiles.getAttributions() as { value: string }[]).map(a => a.value).filter(v => !v.startsWith('<')).join('; ') : ''} · ${(west*180/Math.PI).toFixed(2)}°, ${(south*180/Math.PI).toFixed(2)}° to ${(eastEdge*180/Math.PI).toFixed(2)}°, ${(northEdge*180/Math.PI).toFixed(2)}°`;
    canvas.dataset.tiles = String(loaded);
  });
}
main().catch(error => { info.textContent = String(error); });
