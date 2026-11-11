'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { NetworkError, ApiError, AuthError } = require('./errors');

/**
 * Actions that could not reach the server. Each keeps its ORIGINAL
 * Idempotency-Key, so the server applies it only once even if an earlier
 * try actually got through.
 * Item: { id, method, path, body, key, createdAt, label }
 */
function createPendingQueue({ filePath, send, fsImpl = fs, now = () => Date.now() }) {
  let items = [];
  let flushing = null;

  function load() {
    try {
      const parsed = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'));
      items = Array.isArray(parsed) ? parsed.filter((i) => i && i.key && i.path && i.method) : [];
    } catch (e) {
      items = [];
    }
  }

  function save() {
    fsImpl.mkdirSync(path.dirname(filePath), { recursive: true });
    fsImpl.writeFileSync(filePath, JSON.stringify(items));
  }

  load();

  function add({ method, path: urlPath, body, key, label }) {
    const item = { id: key, method, path: urlPath, body, key, label: label || '', createdAt: now() };
    if (!items.some((i) => i.key === key)) items.push(item);
    save();
    return item;
  }

  /**
   * Try to send everything, oldest first. Stops at the first network problem.
   * Returns a list of { item, outcome: 'sent'|'dropped', message, data? }.
   * 2xx -> removed. 4xx -> removed (server said no). 5xx/network -> kept for later.
   */
  function flush() {
    if (flushing) return flushing;
    flushing = (async () => {
      const results = [];
      for (const item of [...items]) {
        try {
          const res = await send(item);
          items = items.filter((i) => i.key !== item.key);
          save();
          results.push({ item, outcome: 'sent', message: (res.data && res.data.message) || '', data: res.data });
        } catch (e) {
          if (e instanceof NetworkError || e instanceof AuthError) break;
          if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
            items = items.filter((i) => i.key !== item.key);
            save();
            results.push({ item, outcome: 'dropped', message: e.message });
            continue;
          }
          break; // server trouble (5xx): keep and try again later
        }
      }
      return results;
    })();
    const done = () => {
      flushing = null;
    };
    flushing.then(done, done);
    return flushing;
  }

  return {
    add,
    flush,
    list: () => items.slice(),
    count: () => items.length,
    clear() {
      items = [];
      save();
    },
  };
}

module.exports = { createPendingQueue };
