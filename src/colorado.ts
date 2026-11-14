/** Single-resolution portable Colorado model preview. No tiles or LOD controller. */
import { Application, Color, Entity, FILLMODE_FILL_WINDOW, RESOLUTION_AUTO, TONEMAP_ACES, createGraphicsDevice } from 'playcanvas';
import type { Asset, ContainerResource } from 'playcanvas';
import { Orbit } from './orbit';
import { createAtmosphere } from './colorado-atmosphere';

const canvas = document.querySelector<HTMLCanvasElement>('#terrain')!;
const info = document.querySelector<HTMLDivElement>('#info')!;
const root = (import.meta.env.VITE_COLORADO_ROOT as string | undefined)?.replace(/\/$/, '') ?? `${import.meta.env.BASE_URL}colorado-globe`;
async function main() {
  const device = await createGraphicsDevice(canvas, { deviceTypes: ['webgl2'], antialias: true });
  const app = new Application(canvas, { graphicsDevice: device });
  app.setCanvasFillMode(FILLMODE_FILL_WINDOW); app.setCanvasResolution(RESOLUTION_AUTO);
  app.graphicsDevice.maxPixelRatio = Math.min(devicePixelRatio, 2);
  const camera = new Entity('camera'); camera.addComponent('camera', { clearColor: new Color(.18,.114,.055), fov: 40, nearClip: .005, farClip: 100, toneMapping: TONEMAP_ACES }); app.root.addChild(camera);
  const sun = new Entity('warm studio light'); sun.addComponent('light', { type:'directional', color:new Color(1,.87,.7), intensity:1.7, castShadows:true, shadowResolution:2048, shadowDistance:5, normalOffsetBias:.01 }); sun.setEulerAngles(55, -35, 0); app.root.addChild(sun);
  app.scene.ambientLight = new Color(.5,.46,.42);
  const asset = await new Promise<Asset>((resolve,reject) => app.assets.loadFromUrl(`${root}/colorado-crown.glb`, 'container', (error, asset) => error || !asset ? reject(error) : resolve(asset)));
  const model = (asset.resource as ContainerResource).instantiateRenderEntity() as Entity; app.root.addChild(model);
  const border = model.findByName('Colorado border'); if (border) border.enabled = false;  // optional guide, off by default
  const atmosphere = createAtmosphere(app.root as Entity);
  document.querySelector<HTMLButtonElement>('#border')!.onclick = event => { if (border) border.enabled = !border.enabled; (event.currentTarget as HTMLButtonElement).setAttribute('aria-pressed', String(border?.enabled ?? false)); };
  document.querySelector<HTMLAnchorElement>('#download')!.href = `${root}/colorado-crown.glb`;
  const orbit = new Orbit(1.6,.25,innerWidth/innerHeight);
  const hero = () => { orbit.x=0; orbit.z=0; orbit.yaw=0; orbit.pitch=.12; orbit.height=.22; orbit.distance=2.55*Math.max(1,1.5/(innerWidth/innerHeight)); };
  const top = () => { orbit.x=0; orbit.z=0; orbit.yaw=0; orbit.pitch=Math.PI/2-.001; orbit.height=.15; orbit.distance=2.65*Math.max(1,1/(innerWidth/innerHeight)); };
  document.querySelector<HTMLButtonElement>('#hero')!.onclick=hero; document.querySelector<HTMLButtonElement>('#top')!.onclick=top;
  // Deep links for review captures: ?view=top and ?outline=1.
  const query = new URLSearchParams(location.search); (query.get('view')==='top' ? top : hero)();
  if (query.get('outline')==='1') document.querySelector<HTMLButtonElement>('#border')!.click();
  const pointers = new Map<number,{x:number,y:number}>(); let pinch=0;
  canvas.addEventListener('contextmenu',event=>event.preventDefault());
  canvas.addEventListener('pointerdown',event=>{ canvas.setPointerCapture(event.pointerId); pointers.set(event.pointerId,{x:event.clientX,y:event.clientY}); pinch=0; });
  canvas.addEventListener('pointermove',event=>{
    const previous=pointers.get(event.pointerId); if(!previous)return;
    pointers.set(event.pointerId,{x:event.clientX,y:event.clientY});
    if(pointers.size===2){ const [a,b]=[...pointers.values()]; const distance=Math.hypot(a.x-b.x,a.y-b.y); if(pinch)orbit.zoom((pinch-distance)*3); pinch=distance; }
    else if(event.buttons===2 || event.shiftKey)orbit.pan(event.clientX-previous.x,event.clientY-previous.y);
    else {
      orbit.yaw -= (event.clientX-previous.x)*.005;
      orbit.pitch = Math.max(.08, Math.min(Math.PI/2-.001, orbit.pitch+(event.clientY-previous.y)*.005));
    }
  });
  const release=(event:PointerEvent)=>{pointers.delete(event.pointerId);pinch=0;}; canvas.addEventListener('pointerup',release); canvas.addEventListener('pointercancel',release);
  canvas.addEventListener('wheel',event=>{ event.preventDefault(); orbit.zoom(event.deltaY); },{passive:false});
  addEventListener('resize',()=>{app.resizeCanvas();orbit.resize(innerWidth/innerHeight);});
  app.on('update',()=>{camera.setPosition(...orbit.eye);camera.lookAt(orbit.x,orbit.height,orbit.z);atmosphere(camera.getPosition());});
  info.textContent='South → north · San Juans left · Front Range right · One continuous model · Glow and sun are viewer presentation'; app.start();
}
main().catch(error=>{info.textContent=`Unable to load Colorado model: ${String(error)}`;console.error(error);});
