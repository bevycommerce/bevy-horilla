'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { notificationButtons } = require('../src/core/reminders');

const texts = (kind) => notificationButtons(kind).map((b) => b.text);

test('notification buttons for each kind', () => {
  assert.deepEqual(texts('sign_in'), ['Sign In Now', 'Snooze 15 min']);
  assert.deepEqual(texts('sign_in_followup'), ['Sign In Now', 'Snooze 15 min']);
  assert.deepEqual(texts('sign_out'), ['Sign Out Now', 'Snooze 15 min']);
  assert.deepEqual(texts('midday'), ['Write update', 'Skip Midday (combine)', 'Sign Out']);
  assert.deepEqual(texts('eod'), ['Write update', 'Snooze 15 min']);
  assert.deepEqual(notificationButtons('midday').map((b) => b.action), ['open_update', 'skip_midday', 'sign_out']);
  assert.equal(notificationButtons('eod')[0].action, 'open_update');
  assert.equal(notificationButtons('something_new').length, 2);
});

// These read the source files: they cannot prove runtime behaviour, but they stop
// the safe settings being changed by accident.
const root = path.join(__dirname, '..', 'src');
const read = (...p) => fs.readFileSync(path.join(root, ...p), 'utf8');

test('window is created with the safe settings', () => {
  const src = read('main', 'window.js');
  assert.match(src, /contextIsolation: true/);
  assert.match(src, /nodeIntegration: false/);
  assert.match(src, /sandbox: true/);
  assert.match(src, /setWindowOpenHandler\(\(\) => \(\{ action: 'deny' \}\)\)/);
  assert.match(src, /will-navigate/);
});

test('page has a strict Content-Security-Policy and no network access', () => {
  const html = read('renderer', 'index.html');
  assert.match(html, /Content-Security-Policy/);
  assert.match(html, /default-src 'none'/);
  assert.match(html, /connect-src 'none'/);
  assert.doesNotMatch(html, /unsafe-inline|unsafe-eval/);
});

test('window code never writes server text as HTML', () => {
  assert.doesNotMatch(read('renderer', 'app.js'), /innerHTML|insertAdjacentHTML|document\.write/);
});

test('no Take a Break button in the window', () => {
  const all = read('renderer', 'app.js') + read('renderer', 'index.html');
  assert.doesNotMatch(all, /Take a Break/i);
});

test('no em dashes in user-facing text', () => {
  for (const f of [['renderer', 'index.html'], ['renderer', 'app.js'], ['main', 'notifications.js'], ['main', 'tray.js'], ['core', 'reminders.js']]) {
    assert.doesNotMatch(read(...f), /—/, f.join('/'));
  }
});

test('no late or on-time wording in the window', () => {
  const all = read('renderer', 'app.js') + read('renderer', 'index.html');
  assert.doesNotMatch(all, /\blate\b|on[- ]time/i);
});

test('delete confirm text is exactly the agreed sentence', () => {
  assert.match(read('renderer', 'index.html'), /Delete this update\? It will be removed completely and cannot be brought back\./);
});

test('window can be dragged by its top bar; buttons stay clickable', () => {
  const css = read('renderer', 'styles.css');
  assert.match(css, /\.top \{[^}]*-webkit-app-region: drag/);
  assert.match(css, /\.top button[^{]*\{ -webkit-app-region: no-drag/);
  const win = read('main', 'window.js');
  assert.doesNotMatch(win, /on\('blur'/);
  assert.match(win, /on\('moved'/);
});
