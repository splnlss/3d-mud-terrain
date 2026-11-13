/** Capture the relief tileset preview in headless Chrome after tiles have had real time to load.
 *  usage: node scripts/relief-shot.mjs URL OUTPUT.png [seconds] */
import { spawn } from 'node:child_process';
import { rm, writeFile } from 'node:fs/promises';

const [url, output, seconds = '25'] = process.argv.slice(2);
if (!url || !output) throw new Error('Usage: node scripts/relief-shot.mjs URL OUTPUT.png [seconds]');
// The throwaway browser profile goes where RELIEF_TMP points (the external drive), and is removed afterwards.
const profile = `${process.env.RELIEF_TMP ?? '/tmp'}/relief-shot-profile`;
const chrome = spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', ['--headless=new', '--use-angle=metal', '--enable-gpu',
  '--hide-scrollbars', '--window-size=1500,950', '--remote-debugging-port=9377', `--user-data-dir=${profile}`, 'about:blank'], { stdio: 'ignore' });
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
try {
  let target;
  for (let i = 0; i < 40 && !target; i++) {
    await sleep(250);
    try { target = (await (await fetch('http://localhost:9377/json')).json()).find(t => t.type === 'page'); } catch { /* not up yet */ }
  }
  const socket = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  let id = 0; const pending = new Map(); const messages = [];
  socket.addEventListener('message', event => {
    const message = JSON.parse(event.data);
    if (message.id) pending.get(message.id)?.(message.result);
    else if (message.method === 'Runtime.exceptionThrown') messages.push(message.params.exceptionDetails.exception?.description ?? message.params.exceptionDetails.text);
    else if (message.method === 'Runtime.consoleAPICalled' && ['error', 'warning'].includes(message.params.type)) messages.push(message.params.args.map(a => a.value ?? a.description).join(' '));
  });
  const send = (method, params = {}) => new Promise(resolve => { pending.set(++id, resolve); socket.send(JSON.stringify({ id, method, params })); });
  await send('Runtime.enable'); await send('Page.enable'); await send('Page.navigate', { url });
  await sleep(Number(seconds) * 1000);
  const text = await send('Runtime.evaluate', { expression: "document.querySelector('#info').textContent" });
  const shot = await send('Page.captureScreenshot', { format: 'png' });
  await writeFile(output, Buffer.from(shot.data, 'base64'));
  console.log(text.result.value); for (const line of [...new Set(messages)].slice(0, 8)) console.log('console:', line);
  socket.close();
} finally { chrome.kill(); await sleep(500); await rm(profile, { recursive: true, force: true }); }
