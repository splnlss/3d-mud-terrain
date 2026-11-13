/** Verify the visible Paradev preview over CDP. No system browser profile needed. */
import { execFileSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const [workspace, pane, output = 'data/evidence', url = 'http://localhost:20000'] = process.argv.slice(2);
const flags = new Set(process.argv.slice(6));
const mobile = flags.has('--mobile');
if (!workspace || !pane) throw new Error('Usage: node scripts/check-browser.mjs WORKSPACE PANE [OUTPUT] [URL]');
const endpoint = JSON.parse(execFileSync('paradev', ['browser', 'cdp', '--workspace', workspace,
  '--pane', pane, '--json'], { encoding: 'utf8' }));
const socket = new WebSocket(endpoint.url);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});
let id = 0;
const pending = new Map();
const errors = [], requests = [];
const transfers = new Map();
socket.addEventListener('message', event => {
  const message = JSON.parse(event.data);
  if (message.id) {
    const waiter = pending.get(message.id);
    if (waiter) {
      clearTimeout(waiter.timer);
      pending.delete(message.id);
      if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
      else waiter.resolve(message.result);
    }
  } else if (message.method === 'Page.screencastFrame') {
    send('Page.screencastFrameAck', { sessionId: message.params.sessionId }).catch(() => {});
  } else if (message.method === 'Runtime.exceptionThrown') {
    errors.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text);
  } else if (message.method === 'Runtime.consoleAPICalled' && message.params.type === 'error') {
    errors.push(message.params.args.map(arg=>arg.value ?? arg.description ?? arg.type).join(' '));
  } else if (message.method === 'Network.loadingFailed' && !message.params.canceled) {
    errors.push(message.params.errorText);
  } else if (message.method === 'Network.responseReceived') {
    const response = message.params.response;
    if (response.status >= 400) errors.push(`${response.status}: ${response.url}`);
    requests.push({ url: response.url, status: response.status });
  } else if (message.method === 'Network.loadingFinished') {
    transfers.set(message.params.requestId, message.params.encodedDataLength);
  }
});
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const next = ++id;
    const timer = setTimeout(() => {
      pending.delete(next);
      reject(new Error(`CDP timeout: ${method}`));
    }, 15000);
    pending.set(next, { resolve, reject, timer });
    socket.send(JSON.stringify({ id: next, method, params }));
  });
}
async function evaluate(expression) {
  const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
  return result.result.value;
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function until(expression, timeout = 30000) {
  const start = Date.now();
  while (Date.now()-start < timeout) {
    if (await evaluate(expression)) return;
    await pause(250);
  }
  throw new Error(`Page condition timed out: ${expression}`);
}
async function capture(name) {
  const result = await send('Page.captureScreenshot', { format: 'png' });
  await writeFile(join(output, name), Buffer.from(result.data, 'base64'));
  // A native canvas capture avoids the embedded pane cropping an emulated viewport.
  const canvas = await evaluate(`new Promise(resolve=>requestAnimationFrame(()=>resolve(document.querySelector('canvas').toDataURL('image/png'))))`);
  await writeFile(join(output,name.replace('.png','-terrain.png')), Buffer.from(canvas.split(',')[1],'base64'));
  const jpeg = await evaluate(`new Promise(resolve=>requestAnimationFrame(()=>resolve(document.querySelector('canvas').toDataURL('image/jpeg',0.85))))`);
  await writeFile(join(output,name.replace('.png','-review.jpg')), Buffer.from(jpeg.split(',')[1],'base64'));
}

try {
  await mkdir(output, { recursive: true });
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.setCacheDisabled', { cacheDisabled: true });
  await send('Emulation.setDeviceMetricsOverride', {
    width: mobile ? 390 : 1280, height: mobile ? 844 : 720,
    deviceScaleFactor: mobile ? 3 : 2, mobile,
  });
  await send('Page.bringToFront');
  // The embedded pane suspends animation when uncaptured. Screencast keeps it active.
  await send('Page.startScreencast', { format: 'jpeg', quality: 10, maxWidth: 320, maxHeight: 180 });
  await send('Page.navigate', { url });
  await until('document.querySelector("canvas")?.dataset.engine === "PlayCanvas" && document.querySelector("#status").hidden');
  await pause(1500);
  await capture('overview.png');
  const firstView = await evaluate(`({
    navigation:performance.getEntriesByType('navigation')[0].transferSize,
    resources:performance.getEntriesByType('resource').map(r=>({url:r.name,bytes:r.transferSize,encoded:r.encodedBodySize})),
    viewport:[innerWidth,innerHeight,devicePixelRatio]
  })`);
  firstView.totalTransferred = firstView.navigation+firstView.resources.reduce((sum,entry)=>sum+entry.bytes,0);
  firstView.networkTransferred = [...transfers.values()].reduce((sum,bytes)=>sum+bytes,0);
  await writeFile(join(output,'first-view.json'),JSON.stringify(firstView,null,2));
  const viewport = await evaluate('({width:innerWidth,height:innerHeight})');
  const cx = viewport.width*.53, cy = viewport.height*.53;
  const before = await evaluate('document.querySelector("canvas").dataset.camera');
  await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: cx, y: cy, button: 'left', buttons: 1, clickCount: 1 });
  for (let step=1; step<=8; step++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: cx+step*viewport.width*.006, y: cy+step, button: 'left', buttons: 1 });
  }
  await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: cx+viewport.width*.048, y: cy+8, button: 'left', buttons: 0, clickCount: 1 });
  await pause(1200);
  const after = await evaluate('document.querySelector("canvas").dataset.camera');
  assert.notEqual(before, after, 'orbit drag must change the camera');
  for (let step=0; !flags.has('--single') && step<4; step++) {
    await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: cx, y: cy, deltaX: 0, deltaY: -1000 });
    await pause(350);
  }
  if (!flags.has('--single')) await until('Number(document.querySelector("canvas").dataset.loaded)>1');
  await pause(4000);
  await capture('close.png');
  if (flags.has('--views')) {
    const names = await evaluate('[...document.querySelectorAll("#view-preset option")].map(o=>o.value).filter(Boolean)');
    for (const name of names) {
      await evaluate(`(()=>{const s=document.querySelector('#view-preset');s.value=${JSON.stringify(name)};s.dispatchEvent(new Event('change'));})()`);
      await pause(3500);
      await capture(name.toLowerCase().replaceAll(' ','-')+'.png');
    }
  }
  if (flags.has('--clip')) {
    await evaluate(`(()=>{const s=document.querySelector('#view-preset');s.value='Sanchez Reservoir';s.dispatchEvent(new Event('change'));})()`);
    await pause(2500);
    const recording = await evaluate(`new Promise((resolve,reject)=>{
      const stream=document.querySelector('canvas').captureStream(30);
      const type=MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm';
      const recorder=new MediaRecorder(stream,{mimeType:type,videoBitsPerSecond:4000000});
      const chunks=[]; recorder.ondataavailable=e=>chunks.push(e.data);
      recorder.onerror=e=>reject(new Error('Canvas recording failed'));
      recorder.onstop=()=>{stream.getTracks().forEach(t=>t.stop());const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.readAsDataURL(new Blob(chunks,{type}));};
      recorder.start();setTimeout(()=>recorder.stop(),8000);
    })`);
    await writeFile(join(output,'water-shimmer.webm'),Buffer.from(recording.split(',')[1],'base64'));
    await pause(1500);
  }
  if (flags.has('--trace')) {
    // Timing needs a visible, focused pane. Screencasting is only for still/clip
    // capture; do not perturb the measurement or force an otherwise paused pane.
    await send('Page.stopScreencast');
    await send('Network.setCacheDisabled',{cacheDisabled:false});
    await evaluate(`delete document.querySelector('canvas').dataset.trace`);
    await evaluate(`[...document.querySelectorAll('#diagnostics button')].find(b=>b.textContent.includes('Record 60')).click()`);
    for (let step=0; step<75; step++) {
      if (await evaluate('Boolean(document.querySelector("canvas").dataset.trace)')) break;
      const button = step%3===0 ? 'right' : 'left', buttons = button==='right' ? 2 : 1;
      await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: cx, y: cy, button, buttons, clickCount: 1 });
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: cx+(step%20<10 ? 8 : -8), y: cy, button, buttons });
      await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: cx+8, y: cy, button, buttons: 0, clickCount: 1 });
      if (step%5===0) await send('Input.dispatchMouseEvent', { type: 'mouseWheel', x: cx, y: cy, deltaX: 0, deltaY: step%10===0 ? 40 : -40 });
      await pause(1000);
    }
    const trace = await evaluate('JSON.parse(document.querySelector("canvas").dataset.trace)');
    trace.capture={screencast:false,cacheDisabled:false,host:'Visible Paradev pane; navigation via CDP'};
    await writeFile(join(output,'trace.json'),JSON.stringify(trace,null,2));
  }
  const state = await evaluate(`({
    engine:document.querySelector('canvas').dataset.engine,
    dataset:{...document.querySelector('canvas').dataset},
    metrics:document.querySelector('#metrics').value,
    viewport:[innerWidth,innerHeight,devicePixelRatio],
    browser:navigator.userAgent,
    resources:performance.getEntriesByType('resource').map(r=>({url:r.name,bytes:r.transferSize,encoded:r.encodedBodySize}))
  })`);
  if (flags.has('--single')) assert.equal(Number(state.dataset.loaded),1,'single-tile scene must load one GLB');
  else assert.ok(requests.some(request => /tiles\/[1-4]\//.test(request.url)), 'zoom must request a child LOD');
  assert.deepEqual(errors, [], 'no runtime exceptions or failed requests');
  await writeFile(join(output, 'browser.json'), JSON.stringify({ state, requests, errors,
    note: mobile ? 'Mobile viewport emulation on desktop; not a physical phone qualification.' : 'Desktop preview smoke test, not a mobile performance qualification.' }, null, 2));
  console.log(JSON.stringify({ metrics: state.metrics, engine: state.engine,
    loaded: state.dataset.loaded, firstViewBytes: firstView.totalTransferred,
    gpuBytes: state.dataset.gpuBytes, requests: requests.length, errors: errors.length, output }));
  await evaluate('document.querySelector("#reset").click()');
} finally {
  await send('Page.stopScreencast').catch(() => {});
  await send('Network.setCacheDisabled', { cacheDisabled: false }).catch(() => {});
  await send('Emulation.clearDeviceMetricsOverride').catch(() => {});
  socket.close();
}
