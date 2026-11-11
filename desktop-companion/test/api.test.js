'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { createApiClient } = require('../src/core/api');
const { NetworkError, ApiError, AuthError } = require('../src/core/errors');
const { jsonResponse, fakeFetch, memoryTokenStore } = require('./helpers');

const SERVER = 'https://hr.example.com';

function make(script, tokens = memoryTokenStore('refresh-1')) {
  const fetchImpl = fakeFetch(script);
  const api = createApiClient({ fetchImpl, getServerUrl: () => SERVER, tokenStore: tokens, timeoutMs: 1000 });
  return { api, fetchImpl, tokens };
}

test('login stores the refresh token, keeps the access token in memory, never the password', async () => {
  const saved = [];
  const tokens = { ...memoryTokenStore(), save: (t) => saved.push(t) };
  const { api, fetchImpl } = make([jsonResponse(200, { access: 'acc-1', refresh: 'ref-1', employee: { full_name: 'Ann Lee' } })], tokens);
  const who = await api.login('ann', 'secret-password');
  assert.equal(who.name, 'Ann Lee');
  assert.deepEqual(saved, ['ref-1']);
  assert.equal(fetchImpl.calls[0].url, SERVER + '/api/auth/login/');
  assert.deepEqual(fetchImpl.calls[0].body, { username: 'ann', password: 'secret-password' });
  assert.equal(fetchImpl.calls[0].headers.Authorization, undefined);
  assert.ok(!JSON.stringify(saved).includes('secret-password'));
});

test('login with wrong password gives a plain message', async () => {
  const { api } = make([jsonResponse(401, { error: 'Invalid credentials' })]);
  await assert.rejects(api.login('a', 'b'), (e) => e instanceof ApiError && /not correct/.test(e.message));
});

test('request sends Bearer token, X-Workspace-Client and Idempotency-Key', async () => {
  const { api, fetchImpl } = make([
    jsonResponse(200, { access: 'acc-1', refresh: 'refresh-2' }), // first request needs an access token
    jsonResponse(200, { ok: true, message: 'Signed in.' }),
  ]);
  const res = await api.request('POST', '/api/workspace/v1/sign-in/', { body: {}, key: 'key-abc-123' });
  assert.equal(res.data.message, 'Signed in.');
  const call = fetchImpl.calls[1];
  assert.equal(call.headers.Authorization, 'Bearer acc-1');
  assert.equal(call.headers['X-Workspace-Client'], 'desktop');
  assert.equal(call.headers['Idempotency-Key'], 'key-abc-123');
  assert.equal(call.url, SERVER + '/api/workspace/v1/sign-in/');
});

test('GET requests carry no Idempotency-Key', async () => {
  const { api, fetchImpl } = make([jsonResponse(200, { access: 'a', refresh: 'r2' }), jsonResponse(200, { ok: true })]);
  await api.request('GET', '/api/workspace/v1/status/');
  assert.equal(fetchImpl.calls[1].headers['Idempotency-Key'], undefined);
});

test('a 401 triggers one refresh, saves the rotated token, and retries once with the same key', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api, fetchImpl } = make(
    [
      jsonResponse(200, { access: 'acc-old', refresh: 'refresh-2' }),
      jsonResponse(401, { detail: 'Token expired' }),
      jsonResponse(200, { access: 'acc-new', refresh: 'refresh-3' }),
      jsonResponse(200, { ok: true, message: 'done' }),
    ],
    tokens,
  );
  const res = await api.request('POST', '/api/workspace/v1/sign-out/', { body: {}, key: 'key-same-1' });
  assert.equal(res.data.message, 'done');
  assert.equal(fetchImpl.calls.length, 4);
  assert.equal(fetchImpl.calls[2].url, SERVER + '/api/auth/refresh/');
  assert.deepEqual(fetchImpl.calls[2].body, { refresh: 'refresh-2' });
  assert.equal(fetchImpl.calls[3].headers.Authorization, 'Bearer acc-new');
  assert.equal(fetchImpl.calls[3].headers['Idempotency-Key'], 'key-same-1');
  assert.equal(tokens.load(), 'refresh-3');
});

test('two 401 answers in a row end the session (no loop)', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api, fetchImpl } = make(
    [
      jsonResponse(200, { access: 'a1', refresh: 'r2' }),
      jsonResponse(401, {}),
      jsonResponse(200, { access: 'a2', refresh: 'r3' }),
      jsonResponse(401, {}),
    ],
    tokens,
  );
  await assert.rejects(api.request('GET', '/api/workspace/v1/status/'), AuthError);
  assert.equal(fetchImpl.calls.length, 4);
  assert.equal(tokens.load(), null);
});

test('refresh rejected by the server clears the tokens and asks for login', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api } = make([jsonResponse(401, { detail: 'Token is blacklisted' })], tokens);
  await assert.rejects(api.request('GET', '/api/workspace/v1/status/'), AuthError);
  assert.equal(tokens.load(), null);
});

test('no connection during refresh keeps the saved login', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api } = make([() => { throw new TypeError('fetch failed'); }], tokens);
  await assert.rejects(api.request('GET', '/api/workspace/v1/status/'), NetworkError);
  assert.equal(tokens.load(), 'refresh-1');
});

test('a thrown fetch becomes NetworkError', async () => {
  const { api } = make([jsonResponse(200, { access: 'a', refresh: 'r2' }), () => { throw new TypeError('fetch failed'); }]);
  await assert.rejects(api.request('POST', '/x/', { body: {}, key: 'key-12345' }), NetworkError);
});

test('server error message is passed on (and 4xx is an ApiError)', async () => {
  const { api } = make([jsonResponse(200, { access: 'a', refresh: 'r2' }), jsonResponse(409, { ok: false, code: 'duplicate', message: 'You already sent this update.' })]);
  await assert.rejects(api.request('POST', '/x/', { body: {}, key: 'key-12345' }), (e) => e instanceof ApiError && e.status === 409 && e.message === 'You already sent this update.' && e.code === 'duplicate');
});

test('Django validation errors give a readable message', async () => {
  const { api } = make([jsonResponse(200, { access: 'a', refresh: 'r2' }), jsonResponse(400, { summary: ['This field may not be blank.'] })]);
  await assert.rejects(api.request('POST', '/x/', { body: {}, key: 'key-12345' }), (e) => e.message === 'This field may not be blank.');
});

test('logout calls the API with the refresh token and clears tokens', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api, fetchImpl } = make([jsonResponse(200, {})], tokens);
  const r = await api.logout();
  assert.equal(r.serverConfirmed, true);
  assert.equal(fetchImpl.calls[0].url, SERVER + '/api/auth/logout/');
  assert.deepEqual(fetchImpl.calls[0].body, { refresh: 'refresh-1' });
  assert.equal(tokens.load(), null);
  assert.equal(api.hasSession(), false);
});

test('logout still clears tokens when the server cannot be reached', async () => {
  const tokens = memoryTokenStore('refresh-1');
  const { api } = make([() => { throw new TypeError('offline'); }], tokens);
  const r = await api.logout();
  assert.equal(r.serverConfirmed, false);
  assert.equal(tokens.load(), null);
});

test('only one refresh runs when several requests fail together', async () => {
  const tokens = memoryTokenStore('refresh-1');
  let refreshCalls = 0;
  const fetchImpl = async (url, init) => {
    if (url.endsWith('/api/auth/refresh/')) {
      refreshCalls += 1;
      return jsonResponse(200, { access: 'acc-' + refreshCalls, refresh: 'ref-' + (refreshCalls + 1) });
    }
    return jsonResponse(200, { ok: true });
  };
  const api = createApiClient({ fetchImpl, getServerUrl: () => SERVER, tokenStore: tokens });
  await Promise.all([api.request('GET', '/a/'), api.request('GET', '/b/'), api.request('GET', '/c/')]);
  assert.equal(refreshCalls, 1);
});
