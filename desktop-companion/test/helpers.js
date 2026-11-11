'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

function tmpDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'bevy-test-'));
}

/** Stand-in for Electron safeStorage. Not real crypto: it just scrambles the text. */
function fakeSafeStorage(available = true) {
  return {
    isEncryptionAvailable: () => available,
    encryptString: (s) => Buffer.from(Buffer.from(s, 'utf8').map((b) => b ^ 0x5a)),
    decryptString: (buf) => Buffer.from(Buffer.from(buf).map((b) => b ^ 0x5a)).toString('utf8'),
  };
}

function jsonResponse(status, body) {
  return { status, text: async () => (body === undefined ? '' : JSON.stringify(body)) };
}

/**
 * A fake fetch. `script` is a list of functions or responses, used in order.
 * Records every call as { url, method, headers, body }.
 */
function fakeFetch(script) {
  const calls = [];
  const queue = [...script];
  const fn = async (url, init = {}) => {
    calls.push({ url, method: init.method, headers: init.headers || {}, body: init.body ? JSON.parse(init.body) : undefined });
    const next = queue.shift();
    if (!next) throw new Error('fakeFetch: no more scripted answers for ' + url);
    if (typeof next === 'function') return next(url, init);
    return next;
  };
  fn.calls = calls;
  return fn;
}

function memoryTokenStore(initial = null) {
  let token = initial;
  return {
    save: (t) => { token = t; },
    load: () => token,
    clear: () => { token = null; },
    persistent: () => true,
  };
}

module.exports = { tmpDir, fakeSafeStorage, jsonResponse, fakeFetch, memoryTokenStore };
