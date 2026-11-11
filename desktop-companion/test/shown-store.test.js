'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { createShownStore } = require('../src/core/shown-store');
const { tmpDir } = require('./helpers');

test('a reminder already shown is not shown again after a restart', () => {
  const file = path.join(tmpDir(), 'shown.json');
  const day = () => '2026-11-11';
  const first = createShownStore({ filePath: file, today: day });
  assert.deepEqual(first.fresh([{ id: 1 }, { id: 2 }]).map((r) => r.id), [1, 2]);
  first.add(1);
  const second = createShownStore({ filePath: file, today: day });
  assert.deepEqual(second.fresh([{ id: 1 }, { id: 2 }]).map((r) => r.id), [2]);
});

test('a new day starts with an empty list', () => {
  const file = path.join(tmpDir(), 'shown.json');
  createShownStore({ filePath: file, today: () => '2026-11-11' }).add(7);
  const next = createShownStore({ filePath: file, today: () => '2026-11-12' });
  assert.equal(next.has(7), false);
});

test('the day can roll over while the app keeps running', () => {
  const file = path.join(tmpDir(), 'shown.json');
  let day = '2026-11-11';
  const store = createShownStore({ filePath: file, today: () => day });
  store.add(5);
  assert.equal(store.has(5), true);
  day = '2026-11-12';
  assert.equal(store.has(5), false);
});
