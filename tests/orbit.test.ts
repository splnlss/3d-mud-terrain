import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Orbit } from '../src/orbit.ts';

test('repeated touch and wheel input cannot escape the diorama or cross the horizon', () => {
  const orbit = new Orbit(100, 10);
  for (let i=0; i<100; i++) { orbit.rotate(10, -100); orbit.zoom(-10000); orbit.pan(1000, 1000); }
  assert.equal(orbit.distance, 1.5);
  assert.equal(orbit.pitch, .35);
  assert.ok(Math.abs(orbit.x)<=50 && Math.abs(orbit.z)<=50);
  assert.ok(orbit.eye[1]>10);
  for (let i=0; i<100; i++) { orbit.rotate(0, 100); orbit.zoom(10000); }
  assert.equal(orbit.distance, 250);
  assert.equal(orbit.pitch, 1.2);
});

test('portrait overview frames the full square and resizing preserves relative zoom', () => {
  const orbit = new Orbit(100,10);
  orbit.resize(.5);
  const visibleWidth = 2*orbit.distance*Math.tan(19*Math.PI/180)*.5;
  assert.ok(visibleWidth>=100*Math.SQRT2);
  const relative = orbit.distance/orbit.maxDistance;
  orbit.resize(16/9);
  assert.ok(Math.abs(orbit.distance/orbit.maxDistance-relative)<.00001);
});
