import { test } from 'node:test';
import assert from 'node:assert/strict';
import { FrameTrace } from '../src/trace.ts';

test('frame timing excludes the first sample and reports stalls and peak allocations', () => {
  const trace = new FrameTrace(1000);
  assert.equal(trace.add(0, 1, 100), null);
  for (let i=1; i<60; i++) assert.equal(trace.add(i*16, 10, 200), null);
  const result = trace.add(1100, 25, 900)!;
  assert.equal(result.frames, 60);
  assert.equal(result.peakDraws, 25);
  assert.equal(result.peakGpuBytes, 900);
  assert.ok(Math.abs(result.fps-54.54545)<.001);
  assert.equal(result.p95Ms, 16);
  assert.equal(result.within16_7Percent, 59/60*100);
});

test('an interrupted trace is explicitly invalid', () => {
  const trace = new FrameTrace(100);
  trace.add(0, 1, 1);
  trace.invalidate('Page was hidden');
  const result = trace.add(100, 1, 1)!;
  assert.equal(result.valid, false);
  assert.deepEqual(result.reasons, ['Page was hidden']);
});
