'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { createSettingsStore, NO_POSITION } = require('../src/core/settings-store');

test('window position is remembered, and bad values are ignored', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'bevyloop-settings-'));
  const file = path.join(dir, 'settings.json');
  const s1 = createSettingsStore({ filePath: file });
  assert.equal(s1.get().windowX, NO_POSITION);
  s1.set({ windowX: 300, windowY: 120 });
  assert.deepEqual([createSettingsStore({ filePath: file }).get().windowX, createSettingsStore({ filePath: file }).get().windowY], [300, 120]);
  s1.set({ windowX: 'far away' });
  assert.equal(s1.get().windowX, 300);
  fs.writeFileSync(file, JSON.stringify({ windowX: null, windowY: 'x' }));
  assert.equal(createSettingsStore({ filePath: file }).get().windowX, NO_POSITION);
  fs.rmSync(dir, { recursive: true, force: true });
});
