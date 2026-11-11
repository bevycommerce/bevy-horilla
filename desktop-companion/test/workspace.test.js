'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { createWorkspace, OFFLINE_MESSAGE } = require('../src/core/workspace');
const { createPendingQueue } = require('../src/core/pending-queue');
const { NetworkError, ApiError, AuthError } = require('../src/core/errors');
const { tmpDir } = require('./helpers');

function make(request) {
  const queue = createPendingQueue({ filePath: path.join(tmpDir(), 'p.json'), send: async () => ({}) });
  let n = 0;
  const ws = createWorkspace({ api: { request }, queue, uuid: () => 'uuid-key-' + ++n });
  return { ws, queue };
}

test('each click gets a fresh key and the server message is shown on success', async () => {
  const seen = [];
  const { ws } = make(async (m, p, o) => { seen.push([m, p, o.key]); return { data: { ok: true, message: 'You are signed in.' } }; });
  const a = await ws.signIn();
  await ws.signIn();
  assert.equal(a.ok, true);
  assert.equal(a.message, 'You are signed in.');
  assert.deepEqual(seen.map((s) => s[2]), ['uuid-key-1', 'uuid-key-2']);
  assert.equal(seen[0][1], '/api/workspace/v1/sign-in/');
});

test('no connection: not ok, queued with the same key, plain message', async () => {
  let sentKey;
  const { ws, queue } = make(async (m, p, o) => { sentKey = o.key; throw new NetworkError(); });
  const r = await ws.submitUpdate('eod', 'Did things');
  assert.equal(r.ok, false);
  assert.equal(r.queued, true);
  assert.equal(r.message, OFFLINE_MESSAGE);
  assert.equal(OFFLINE_MESSAGE, 'Not saved yet - no connection. We will retry.');
  const item = queue.list()[0];
  assert.equal(item.key, sentKey);
  assert.equal(item.path, '/api/workspace/v1/updates/');
  assert.deepEqual(item.body, { type: 'eod', summary: 'Did things' });
});

test('a server refusal is never shown as success and is not queued', async () => {
  const { ws, queue } = make(async () => { throw new ApiError(409, 'You already sent this update for this day.'); });
  const r = await ws.submitUpdate('midday', 'x');
  assert.equal(r.ok, false);
  assert.equal(r.message, 'You already sent this update for this day.');
  assert.equal(queue.count(), 0);
});

test('a 2xx answer that says ok:false is not shown as success', async () => {
  const { ws } = make(async () => ({ data: { ok: false, message: 'Nope.' } }));
  const r = await ws.signOut();
  assert.equal(r.ok, false);
  assert.equal(r.message, 'Nope.');
});

test('an ended session is reported, not queued', async () => {
  const { ws, queue } = make(async () => { throw new AuthError(); });
  const r = await ws.signIn();
  assert.equal(r.authLost, true);
  assert.equal(queue.count(), 0);
});

test('midday skip sends the choice; snooze sends minutes and no key', async () => {
  const calls = [];
  const { ws } = make(async (m, p, o) => { calls.push([p, o]); return { data: { ok: true } }; });
  await ws.skipMidday('combine');
  await ws.snooze(12, 15);
  assert.equal(calls[0][0], '/api/workspace/v1/updates/midday-skip/');
  assert.deepEqual(calls[0][1].body, { choice: 'combine' });
  assert.equal(calls[1][0], '/api/workspace/v1/reminders/12/snooze/');
  assert.deepEqual(calls[1][1].body, { minutes: 15 });
  assert.equal(calls[1][1].key, undefined);
});
