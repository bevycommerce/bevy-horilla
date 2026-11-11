'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { createWorkspace, OFFLINE_MESSAGE, NEEDS_NETWORK_MESSAGE } = require('../src/core/workspace');
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

test('edit sends PATCH with the four fields and a fresh key', async () => {
  const seen = [];
  const { ws } = make(async (m, p, o) => { seen.push([m, p, o]); return { data: { ok: true, message: 'Update saved.', update: { id: 7 } } }; });
  const a = await ws.editUpdate(7, { summary: 'New text', completed: 'a', ongoing: 'b', blockers: 'c' });
  await ws.editUpdate(7, { summary: 'Again' });
  assert.equal(a.ok, true);
  assert.equal(a.message, 'Update saved.');
  assert.equal(seen[0][0], 'PATCH');
  assert.equal(seen[0][1], '/api/workspace/v1/updates/7/');
  assert.deepEqual(seen[0][2].body, { summary: 'New text', completed: 'a', ongoing: 'b', blockers: 'c' });
  assert.deepEqual(seen[1][2].body, { summary: 'Again', completed: '', ongoing: '', blockers: '' });
  assert.deepEqual([seen[0][2].key, seen[1][2].key], ['uuid-key-1', 'uuid-key-2']);
});

test('delete sends DELETE with a key and no body, and returns the server message and day', async () => {
  let seen;
  const { ws } = make(async (m, p, o) => { seen = [m, p, o]; return { data: { ok: true, message: 'Update deleted.', deleted_id: 9, day: { midday: null } } }; });
  const r = await ws.deleteUpdate(9);
  assert.equal(r.ok, true);
  assert.equal(r.message, 'Update deleted.');
  assert.deepEqual(r.data.day, { midday: null });
  assert.equal(seen[0], 'DELETE');
  assert.equal(seen[1], '/api/workspace/v1/updates/9/');
  assert.equal(seen[2].body, undefined);
  assert.equal(seen[2].key, 'uuid-key-1');
});

test('edit and delete offline: not queued, plain offline message', async () => {
  const { ws, queue } = make(async () => { throw new NetworkError(); });
  const e = await ws.editUpdate(1, { summary: 'x' });
  const d = await ws.deleteUpdate(1);
  for (const r of [e, d]) {
    assert.equal(r.ok, false);
    assert.equal(r.offline, true);
    assert.equal(r.queued, undefined);
    assert.equal(r.message, 'You are offline. Please try again when the connection is back.');
  }
  assert.equal(NEEDS_NETWORK_MESSAGE, 'You are offline. Please try again when the connection is back.');
  assert.equal(queue.count(), 0);
});

test('edit and delete: server message shown on refusal, 404 not success, session loss reported', async () => {
  const a = make(async () => { throw new ApiError(404, 'Update not found.'); });
  const r1 = await a.ws.deleteUpdate(5);
  assert.deepEqual([r1.ok, r1.message], [false, 'Update not found.']);
  const b = make(async () => ({ data: { ok: false, message: 'Summary is required.' } }));
  const r2 = await b.ws.editUpdate(5, { summary: '' });
  assert.deepEqual([r2.ok, r2.message], [false, 'Summary is required.']);
  const c = make(async () => { throw new AuthError(); });
  assert.equal((await c.ws.deleteUpdate(5)).authLost, true);
  assert.equal(c.queue.count(), 0);
});

test('edit and delete refuse a bad id before any request', async () => {
  let called = false;
  const { ws } = make(async () => { called = true; return { data: {} }; });
  assert.throws(() => ws.deleteUpdate('../x'), TypeError);
  assert.throws(() => ws.editUpdate(0, { summary: 'x' }), TypeError);
  assert.equal(called, false);
});
