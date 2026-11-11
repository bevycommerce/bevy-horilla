'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createTokenStore } = require('../src/core/token-store');
const { tmpDir, fakeSafeStorage } = require('./helpers');

const SECRET = 'eyJ.refresh-token-value.abc';

test('with safeStorage the file never holds the token in plain text', () => {
  const dir = tmpDir();
  const file = path.join(dir, 'session.json');
  const store = createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(true) });
  store.save(SECRET);
  const onDisk = fs.readFileSync(file, 'utf8');
  assert.ok(!onDisk.includes(SECRET));
  assert.ok(!onDisk.includes(Buffer.from(SECRET).toString('base64')));
  assert.equal(store.persistent(), true);
});

test('a new store instance (app restart) can read the saved token', () => {
  const dir = tmpDir();
  const file = path.join(dir, 'session.json');
  createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(true) }).save(SECRET);
  const again = createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(true) });
  assert.equal(again.load(), SECRET);
});

test('without safeStorage nothing is written to disk and the token lives in memory only', () => {
  const dir = tmpDir();
  const file = path.join(dir, 'session.json');
  const store = createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(false) });
  store.save(SECRET);
  assert.equal(fs.existsSync(file), false);
  assert.equal(store.load(), SECRET);
  assert.equal(store.persistent(), false);
  assert.equal(createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(false) }).load(), null);
});

test('clear removes the file and the memory copy', () => {
  const dir = tmpDir();
  const file = path.join(dir, 'session.json');
  const store = createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(true) });
  store.save(SECRET);
  store.clear();
  assert.equal(fs.existsSync(file), false);
  assert.equal(store.load(), null);
});

test('a damaged file gives no token instead of crashing', () => {
  const dir = tmpDir();
  const file = path.join(dir, 'session.json');
  fs.writeFileSync(file, 'not json');
  assert.equal(createTokenStore({ filePath: file, safeStorage: fakeSafeStorage(true) }).load(), null);
});
