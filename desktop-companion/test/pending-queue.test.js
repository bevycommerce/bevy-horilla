'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { createPendingQueue } = require('../src/core/pending-queue');
const { NetworkError, ApiError } = require('../src/core/errors');
const { tmpDir } = require('./helpers');

function make(send, file) {
  return createPendingQueue({ filePath: file || path.join(tmpDir(), 'pending.json'), send });
}
const item = (key, extra) => ({ method: 'POST', path: '/api/workspace/v1/sign-in/', body: {}, key, label: 'Sign in', ...extra });

test('add stores method, path, body, key and createdAt in the file', () => {
  const file = path.join(tmpDir(), 'pending.json');
  const q = make(async () => ({}), file);
  q.add(item('key-000001'));
  const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
  assert.equal(saved.length, 1);
  assert.deepEqual(Object.keys(saved[0]).sort(), ['body', 'createdAt', 'id', 'key', 'label', 'method', 'path']);
  assert.equal(q.count(), 1);
});

test('waiting actions survive an app restart', () => {
  const file = path.join(tmpDir(), 'pending.json');
  make(async () => ({}), file).add(item('key-000002'));
  assert.equal(make(async () => ({}), file).count(), 1);
});

test('a network failure keeps the item and the retry uses the SAME key', async () => {
  const keys = [];
  let online = false;
  const q = make(async (i) => {
    keys.push(i.key);
    if (!online) throw new NetworkError();
    return { data: { ok: true, message: 'Signed in.' } };
  });
  q.add(item('key-000003'));
  assert.deepEqual(await q.flush(), []);
  assert.equal(q.count(), 1);
  online = true;
  const results = await q.flush();
  assert.deepEqual(keys, ['key-000003', 'key-000003']);
  assert.equal(results[0].outcome, 'sent');
  assert.equal(q.count(), 0);
});

test('a 2xx answer removes the item', async () => {
  const q = make(async () => ({ data: { message: 'ok' } }));
  q.add(item('key-000004'));
  await q.flush();
  assert.equal(q.count(), 0);
});

test('a 4xx answer drops the item and reports the server message', async () => {
  const q = make(async () => { throw new ApiError(409, 'You already sent this update.'); });
  q.add(item('key-000005'));
  const results = await q.flush();
  assert.equal(q.count(), 0);
  assert.equal(results[0].outcome, 'dropped');
  assert.equal(results[0].message, 'You already sent this update.');
});

test('a 5xx answer keeps the item for later', async () => {
  const q = make(async () => { throw new ApiError(502, 'The server had a problem.'); });
  q.add(item('key-000006'));
  await q.flush();
  assert.equal(q.count(), 1);
});

test('items are sent oldest first and sending stops at the first network problem', async () => {
  const order = [];
  const q = make(async (i) => {
    order.push(i.key);
    if (i.key === 'key-000008') throw new NetworkError();
    return { data: {} };
  });
  q.add(item('key-000007'));
  q.add(item('key-000008'));
  q.add(item('key-000009'));
  await q.flush();
  assert.deepEqual(order, ['key-000007', 'key-000008']);
  assert.equal(q.count(), 2);
});

test('the same key is never queued twice', () => {
  const q = make(async () => ({}));
  q.add(item('key-000010'));
  q.add(item('key-000010'));
  assert.equal(q.count(), 1);
});

test('two flushes at the same time send only once', async () => {
  let sends = 0;
  const q = make(async () => { sends += 1; await new Promise((r) => setTimeout(r, 20)); return { data: {} }; });
  q.add(item('key-000011'));
  await Promise.all([q.flush(), q.flush()]);
  assert.equal(sends, 1);
});
