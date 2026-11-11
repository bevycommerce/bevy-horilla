'use strict';

const { NetworkError, ApiError, AuthError } = require('./errors');

const CLIENT_HEADER = 'desktop';

/** Pull a human sentence out of whatever shape the server's error body has. */
function messageFromBody(body, status) {
  if (body && typeof body === 'object') {
    for (const key of ['message', 'error', 'detail']) {
      if (typeof body[key] === 'string' && body[key]) return body[key];
    }
    // Django REST validation errors: { field: ["text"] }
    for (const value of Object.values(body)) {
      if (Array.isArray(value) && typeof value[0] === 'string') return value[0];
      if (typeof value === 'string') return value;
    }
  }
  if (status >= 500) return 'The server had a problem. Please try again in a moment.';
  if (status === 404) return 'The server could not find this. The portal may need an update.';
  return `The server did not accept this request (error ${status}).`;
}

/**
 * Talks to the portal. All network traffic of the app goes through here.
 * Options: { fetchImpl, getServerUrl(), tokenStore, timeoutMs, onSessionEnded() }
 * Throws NetworkError (no connection), ApiError (server said no), AuthError (must log in again).
 */
function createApiClient({ fetchImpl, getServerUrl, tokenStore, timeoutMs = 15000, onSessionEnded }) {
  let accessToken = null;
  let refreshing = null;

  async function rawFetch(method, path, { body, headers = {} } = {}) {
    const base = getServerUrl();
    if (!base) throw new ApiError(0, 'Please set the server address in Settings first.', 'no_server');
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    let response;
    try {
      response = await fetchImpl(base + path, {
        method,
        headers: {
          Accept: 'application/json',
          'X-Workspace-Client': CLIENT_HEADER,
          ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
          ...headers,
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
    } catch (e) {
      throw new NetworkError(e && e.name === 'AbortError' ? 'The server took too long to answer.' : undefined);
    } finally {
      clearTimeout(timer);
    }
    let data = null;
    try {
      const text = await response.text();
      data = text ? JSON.parse(text) : null;
    } catch (e) {
      data = null;
    }
    return { status: response.status, ok: response.status >= 200 && response.status < 300, data };
  }

  function endSession() {
    accessToken = null;
    tokenStore.clear();
    if (onSessionEnded) onSessionEnded();
  }

  /** Swap the refresh token for a new pair. Only one refresh runs at a time. */
  function refresh() {
    if (refreshing) return refreshing;
    refreshing = (async () => {
      const refreshToken = tokenStore.load();
      if (!refreshToken) {
        accessToken = null;
        throw new AuthError();
      }
      const res = await rawFetch('POST', '/api/auth/refresh/', { body: { refresh: refreshToken } });
      if (res.ok && res.data && res.data.access) {
        accessToken = res.data.access;
        if (res.data.refresh) tokenStore.save(res.data.refresh); // refresh tokens rotate
        return accessToken;
      }
      if (res.status === 401 || res.status === 400 || res.status === 403) {
        endSession();
        throw new AuthError();
      }
      throw new ApiError(res.status, messageFromBody(res.data, res.status), null, res.data);
    })();
    const clear = () => {
      refreshing = null;
    };
    refreshing.then(clear, clear);
    return refreshing;
  }

  /**
   * Call a workspace endpoint with the login token.
   * options: { body, key }  (key = Idempotency-Key, sent when given)
   */
  async function request(method, path, options = {}) {
    const { body, key } = options;
    const headers = {};
    if (key) headers['Idempotency-Key'] = key;

    async function attempt() {
      if (!accessToken) await refresh();
      return rawFetch(method, path, { body, headers: { ...headers, Authorization: `Bearer ${accessToken}` } });
    }

    let res = await attempt();
    if (res.status === 401) {
      accessToken = null;
      await refresh(); // throws AuthError if it fails
      res = await attempt();
      if (res.status === 401) {
        endSession();
        throw new AuthError();
      }
    }
    if (!res.ok) {
      throw new ApiError(res.status, messageFromBody(res.data, res.status), res.data && res.data.code, res.data);
    }
    return { status: res.status, data: res.data || {} };
  }

  async function login(username, password) {
    const res = await rawFetch('POST', '/api/auth/login/', { body: { username, password } });
    if (!res.ok) {
      let message = messageFromBody(res.data, res.status);
      if (res.status === 401) message = 'The user name or password is not correct.';
      if (res.status === 429) message = 'Too many tries. Please wait a few minutes and try again.';
      throw new ApiError(res.status, message, null, res.data);
    }
    if (!res.data || !res.data.access || !res.data.refresh) {
      throw new ApiError(res.status, 'The server answer was not what we expected. Is the address correct?');
    }
    accessToken = res.data.access;
    tokenStore.save(res.data.refresh);
    const employee = res.data.employee || {};
    return { name: employee.full_name || username };
  }

  /** Always clears local tokens, even if the server cannot be reached. */
  async function logout() {
    const refreshToken = tokenStore.load();
    let serverConfirmed = false;
    if (refreshToken) {
      try {
        const res = await rawFetch('POST', '/api/auth/logout/', {
          body: { refresh: refreshToken },
          headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
        });
        serverConfirmed = res.ok;
      } catch (e) {
        serverConfirmed = false;
      }
    }
    accessToken = null;
    tokenStore.clear();
    return { serverConfirmed };
  }

  return {
    login,
    logout,
    request,
    refresh,
    hasSession: () => !!(accessToken || tokenStore.load()),
  };
}

module.exports = { createApiClient, messageFromBody };
