'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { validateServerUrl } = require('../src/core/url');
const { formatHMS, currentWorkedSeconds, clockFromIso, localDateKey } = require('../src/core/time');

test('https address is accepted without warning', () => {
  const r = validateServerUrl('https://hr.example.com/');
  assert.equal(r.ok, true);
  assert.equal(r.insecure, false);
  assert.equal(r.url, 'https://hr.example.com');
});

test('http on localhost and 127.0.0.1 is accepted without warning', () => {
  for (const u of ['http://localhost:8000', 'http://127.0.0.1:8000/']) {
    const r = validateServerUrl(u);
    assert.equal(r.ok, true, u);
    assert.equal(r.insecure, false, u);
  }
});

test('http on another host gives a clear warning and needs confirmation', () => {
  const r = validateServerUrl('http://hr.example.com');
  assert.equal(r.ok, true);
  assert.equal(r.insecure, true);
  assert.match(r.warning, /not secure/);
  assert.equal(validateServerUrl('http://192.168.1.20:8000').insecure, true);
});

test('bad addresses are refused with a plain message', () => {
  for (const u of ['', '   ', 'hr.example.com', 'ftp://x.com', 'https://user:pw@x.com', 'javascript:alert(1)']) {
    const r = validateServerUrl(u);
    assert.equal(r.ok, false, u);
    assert.ok(r.error.length > 5);
  }
});

test('a path on the address is dropped', () => {
  assert.equal(validateServerUrl('https://hr.example.com/some/page').url, 'https://hr.example.com');
});

test('timer formatting', () => {
  assert.equal(formatHMS(0), '00:00:00');
  assert.equal(formatHMS(59), '00:00:59');
  assert.equal(formatHMS(3725), '01:02:05');
  assert.equal(formatHMS(36000), '10:00:00');
  assert.equal(formatHMS(-5), '00:00:00');
  assert.equal(formatHMS('abc'), '00:00:00');
  assert.equal(formatHMS(61.9), '00:01:01');
});

test('timer only ticks while the server says it is running', () => {
  const running = { worked_seconds: 100, timer_running: true };
  const stopped = { worked_seconds: 100, timer_running: false };
  assert.equal(currentWorkedSeconds(running, 1000, 6000), 105);
  assert.equal(currentWorkedSeconds(stopped, 1000, 6000), 100);
  assert.equal(currentWorkedSeconds(running, 6000, 1000), 100);
  assert.equal(currentWorkedSeconds(null, 0, 0), 0);
});

test('clock from server time is read as written (no zone change)', () => {
  assert.equal(clockFromIso('2026-11-11T09:02:33.123+06:00'), '09:02');
  assert.equal(clockFromIso(null), '');
});

test('local date key', () => {
  assert.equal(localDateKey(new Date(2026, 10, 5, 23, 59)), '2026-11-05');
});
