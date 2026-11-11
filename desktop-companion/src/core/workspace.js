'use strict';

const crypto = require('node:crypto');
const { NetworkError, ApiError, AuthError } = require('./errors');

const BASE = '/api/workspace/v1/';
const OFFLINE_MESSAGE = 'Not saved yet - no connection. We will retry.';

/**
 * The things the app can ask the portal to do, in plain results.
 * Every change gets a fresh Idempotency-Key at click time. If the network fails,
 * the action goes to the pending queue with that same key.
 * Results: { ok, message, data?, queued?, authLost? }  (never ok:true unless the server answered 2xx)
 */
function createWorkspace({ api, queue: initialQueue, uuid = () => crypto.randomUUID() }) {
  let queue = initialQueue;

  async function change(method, path, body, label) {
    const key = uuid();
    try {
      const res = await api.request(method, path, { body, key });
      if (res.data && res.data.ok === false) {
        return { ok: false, message: res.data.message || 'The server could not do this.' };
      }
      return { ok: true, message: (res.data && res.data.message) || 'Done.', data: res.data };
    } catch (e) {
      if (e instanceof NetworkError) {
        queue.add({ method, path, body, key, label });
        return { ok: false, queued: true, message: OFFLINE_MESSAGE };
      }
      if (e instanceof AuthError) return { ok: false, authLost: true, message: e.message };
      if (e instanceof ApiError) return { ok: false, message: e.message };
      throw e;
    }
  }

  /** Reminder snooze/ack: harmless to repeat, so no key and no queue. */
  async function simple(method, path, body) {
    try {
      const res = await api.request(method, path, { body });
      return { ok: true, data: res.data };
    } catch (e) {
      if (e instanceof AuthError) return { ok: false, authLost: true, message: e.message };
      if (e instanceof NetworkError) return { ok: false, message: 'No connection to the server.' };
      if (e instanceof ApiError) return { ok: false, message: e.message };
      throw e;
    }
  }

  async function read(path) {
    const res = await api.request('GET', path);
    return res.data;
  }

  return {
    /** The queue needs this module's sender, so it is attached after both exist. */
    attachQueue(q) {
      queue = q;
    },
    signIn: () => change('POST', `${BASE}sign-in/`, {}, 'Sign in'),
    signOut: () => change('POST', `${BASE}sign-out/`, {}, 'Sign out'),
    endBreak: () => change('POST', `${BASE}break/end/`, {}, 'End break'),
    submitUpdate: (type, summary) => change('POST', `${BASE}updates/`, { type, summary }, 'Daily update'),
    skipMidday: (choice) => change('POST', `${BASE}updates/midday-skip/`, { choice }, 'Skip Midday'),
    snooze: (id, minutes) => simple('POST', `${BASE}reminders/${Number(id)}/snooze/`, { minutes }),
    ack: (id) => simple('POST', `${BASE}reminders/${Number(id)}/ack/`, {}),
    getStatus: () => read(`${BASE}status/`),
    getDay: () => read(`${BASE}updates/`),
    getReminders: () => read(`${BASE}reminders/`),
  };
}

module.exports = { createWorkspace, OFFLINE_MESSAGE, BASE };
