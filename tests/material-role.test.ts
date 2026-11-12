import { test } from 'node:test';
import assert from 'node:assert/strict';
import { materialRole } from '../src/material-role.ts';

test('PlayCanvas flat-shaded material cloning must not turn water into terrain', () => {
  assert.equal(materialRole('painted-water'), 'water');
  assert.equal(materialRole('painted-water-flatShaded'), 'water');
  assert.equal(materialRole('terrain-flatShaded'), 'terrain');
  assert.equal(materialRole('painted-waterfall'), 'terrain');
  assert.equal(materialRole(null), 'terrain');
});
