import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadTexture } from '../src/texture-load.ts';

test('a texture finishing after timeout releases its GPU resource and registry entry', async () => {
  let callback: (error: unknown, asset?: { unload(): void }) => void = () => {};
  let unloaded = 0, removed = 0;
  const registry = {
    loadFromUrl(_url: string, _type: 'texture', done: typeof callback) { callback = done; },
    remove() { removed++; },
  };
  await assert.rejects(loadTexture(registry, 'late.ktx2', { timeoutMs:5, attempts:1 }), /timed out/);
  callback(null, { unload() { unloaded++; } });
  assert.equal(unloaded, 1);
  assert.equal(removed, 1);
});

test('failed texture loads remove the failed asset and successful loads retain it', async () => {
  let unloaded = 0, removed = 0;
  const asset = { unload() { unloaded++; } };
  const registry = {
    loadFromUrl(url: string, _type: 'texture', done: (error: unknown, loaded?: typeof asset) => void) {
      done(url==='bad' ? 'decode failed' : null, asset);
    },
    remove() { removed++; },
  };
  await assert.rejects(loadTexture(registry, 'bad', { attempts:1 }), /decode failed/);
  assert.equal(await loadTexture(registry, 'good'), asset);
  assert.equal(unloaded, 1);
  assert.equal(removed, 1);
});


test('a queued load does not expire by default and transient errors retry', async () => {
  let attempts=0, removed=0;
  const asset={unload() {}};
  const registry={
    loadFromUrl(_url: string,_type: 'texture',done: (error: unknown,loaded?: typeof asset)=>void) {
      attempts++;
      if (attempts===1) done('temporary network error',asset);
      else setTimeout(()=>done(null,asset),40);
    },
    remove() {removed++;},
  };
  assert.equal(await loadTexture(registry,'retry'),asset);
  assert.equal(attempts,2);
  assert.equal(removed,1);
});
