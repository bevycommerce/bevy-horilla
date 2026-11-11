'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { createController } = require('../src/core/controller');
const { createShownStore } = require('../src/core/shown-store');
const { createSettingsStore } = require('../src/core/settings-store');
const { createPendingQueue } = require('../src/core/pending-queue');
const { NetworkError, AuthError, ApiError } = require('../src/core/errors');
const { tmpDir, memoryTokenStore } = require('./helpers');

function make({ workspace = {}, api = {}, token = 'r1', server = 'https://hr.example.com' } = {}) {
  const dir = tmpDir();
  const settings = createSettingsStore({ filePath: path.join(dir, 's.json') });
  if (server) settings.set({ serverUrl: server });
  const shown = createShownStore({ filePath: path.join(dir, 'shown.json') });
  const queue = createPendingQueue({ filePath: path.join(dir, 'p.json'), send: async () => { throw new NetworkError(); } });
  const notified = [];
  const ws = {
    getStatus: async () => ({ state: { status: 'working', worked_seconds: 60, timer_running: true }, employee: { name: 'Ann' } }),
    getDay: async () => ({ day: { can_submit_midday: true } }),
    getReminders: async () => ({ reminders: [{ id: 1, kind: 'sign_in', message: 'Hi' }], pending_actions: [{ kind: 'eod', label: 'Write' }] }),
    ...workspace,
  };
  const controller = createController({
    api: { login: async () => ({ name: 'Ann' }), logout: async () => ({ serverConfirmed: true }), ...api },
    workspace: ws,
    queue,
    shown,
    settings,
    tokenStore: memoryTokenStore(token),
    onNewReminders: (list) => notified.push(...list.map((r) => r.id)),
  });
  return { controller, notified, queue, settings };
}

test('polling fills the snapshot and notifies each reminder only once', async () => {
  const { controller, notified } = make();
  await controller.poll();
  await controller.poll();
  const snap = controller.snapshot();
  assert.equal(snap.statusLabel, 'Working');
  assert.equal(snap.employeeName, 'Ann');
  assert.equal(snap.pendingActions.length, 1);
  assert.deepEqual(notified, [1]);
});

test('notifications switched off: nothing is shown', async () => {
  const { controller, notified, settings } = make();
  settings.set({ notificationsEnabled: false });
  await controller.poll();
  assert.deepEqual(notified, []);
});

test('no connection keeps old data and flags offline', async () => {
  let fail = false;
  const { controller } = make({ workspace: { getStatus: async () => { if (fail) throw new NetworkError(); return { state: { status: 'working', worked_seconds: 5, timer_running: true }, employee: { name: 'Ann' } }; } } });
  await controller.poll();
  fail = true;
  await controller.poll();
  const snap = controller.snapshot();
  assert.equal(snap.offline, true);
  assert.equal(snap.status.status, 'working');
});

test('an ended session sends the user back to login', async () => {
  const { controller } = make({ workspace: { getStatus: async () => { throw new AuthError(); } } });
  assert.equal(controller.snapshot().loggedIn, true);
  await controller.poll();
  assert.equal(controller.snapshot().loggedIn, false);
});

test('not logged in on first run (no server, no token)', () => {
  const { controller } = make({ token: null, server: '' });
  assert.equal(controller.snapshot().loggedIn, false);
});

test('login: plain http to another host needs confirmation and is not sent', async () => {
  let called = false;
  const { controller } = make({ token: null, server: '', api: { login: async () => { called = true; return { name: 'x' }; } } });
  const r = await controller.login({ serverUrl: 'http://hr.example.com', username: 'a', password: 'b' });
  assert.equal(r.ok, false);
  assert.equal(r.needsConfirm, true);
  assert.equal(called, false);
});

test('login: success stores the server address (never the password)', async () => {
  const { controller, settings } = make({ token: null, server: '' });
  const r = await controller.login({ serverUrl: 'http://localhost:8000', username: 'ann', password: 'secret-pw' });
  assert.equal(r.ok, true);
  assert.equal(controller.snapshot().loggedIn, true);
  assert.ok(!JSON.stringify(settings.get()).includes('secret-pw'));
  assert.equal(settings.get().serverUrl, 'http://localhost:8000');
});

test('login: wrong password shows the message and stays logged out', async () => {
  const { controller, settings } = make({ token: null, server: '', api: { login: async () => { throw new ApiError(401, 'The user name or password is not correct.'); } } });
  const r = await controller.login({ serverUrl: 'http://localhost:8000', username: 'ann', password: 'x' });
  assert.equal(r.ok, false);
  assert.match(r.message, /not correct/);
  assert.equal(settings.get().serverUrl, '');
});

test('logging in as a different person discards the previous person waiting actions', async () => {
  const { controller, queue, settings } = make({ token: null, server: '' });
  settings.set({ loginName: 'ann', serverUrl: 'http://localhost:8000' });
  queue.add({ method: 'POST', path: '/x/', body: {}, key: 'key-000001' });
  await controller.login({ serverUrl: 'http://localhost:8000', username: 'bob', password: 'x' });
  assert.equal(queue.count(), 0);
});

test('the same person logging in again keeps waiting actions', async () => {
  const { controller, queue, settings } = make({ token: null, server: '' });
  settings.set({ loginName: 'ann', serverUrl: 'http://localhost:8000' });
  queue.add({ method: 'POST', path: '/x/', body: {}, key: 'key-000002' });
  await controller.login({ serverUrl: 'http://localhost:8000', username: 'Ann', password: 'x' });
  assert.equal(queue.count(), 1);
});

test('logout clears the session and says so', async () => {
  const { controller } = make();
  const r = await controller.logout();
  assert.equal(r.ok, true);
  assert.equal(controller.snapshot().loggedIn, false);
});

test('an action while the same action is still saving is refused', async () => {
  let release;
  const gate = new Promise((r) => { release = r; });
  const { controller } = make({ workspace: { signIn: async () => { await gate; return { ok: true, message: 'Done' }; } } });
  const first = controller.perform('sign_in');
  const second = await controller.perform('sign_in');
  assert.equal(second.ok, false);
  release();
  assert.equal((await first).ok, true);
});

test('edit and delete update run through perform, refresh the day, and never queue', async () => {
  const calls = [];
  let days = 0;
  const { controller, queue } = make({
    workspace: {
      getDay: async () => { days++; return { day: { can_submit_midday: true } }; },
      editUpdate: async (id, f) => { calls.push(['edit', id, f.summary]); return { ok: true, message: 'Update saved.' }; },
      deleteUpdate: async (id) => { calls.push(['delete', id]); return { ok: true, message: 'Update deleted.' }; },
    },
  });
  await controller.poll();
  const before = days;
  const e = await controller.perform('edit_update', { id: 4, summary: 'Hi' });
  const d = await controller.perform('delete_update', { id: 4 });
  assert.equal(e.message, 'Update saved.');
  assert.equal(d.message, 'Update deleted.');
  assert.deepEqual(calls, [['edit', 4, 'Hi'], ['delete', 4]]);
  assert.equal(days, before + 2);
  assert.equal(queue.count(), 0);
});

test('offline edit shows the offline message and does not refresh as success', async () => {
  const { controller, queue } = make({
    workspace: { editUpdate: async () => ({ ok: false, offline: true, message: 'You are offline. Please try again when the connection is back.' }) },
  });
  const r = await controller.perform('edit_update', { id: 4, summary: 'Hi' });
  assert.equal(r.ok, false);
  assert.match(r.message, /offline/);
  assert.equal(queue.count(), 0);
});
