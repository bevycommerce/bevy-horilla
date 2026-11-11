'use strict';

const { NetworkError, AuthError, ApiError } = require('./errors');
const { validateServerUrl } = require('./url');

const STATUS_LABELS = {
  not_signed_in: 'Not Signed In',
  working: 'Working',
  away: 'Away',
  on_break: 'On Break',
  signed_out: 'Signed Out',
};

/**
 * The app's brain, without any Electron code in it.
 * Holds the latest server answers, polls, retries the pending queue and runs actions.
 *
 * deps: { api, workspace, queue, shown, settings, tokenStore, onChange(snapshot),
 *         onNewReminders(list), extras() -> {appVersion, openAtLogin, canAutoStart}, now() }
 */
function createController(deps) {
  const { api, workspace, queue, shown, settings, tokenStore } = deps;
  const now = deps.now || (() => Date.now());
  let tentativeUrl = null; // used only while logging in
  let polling = null;
  let flushing = null;
  const inFlight = new Set();

  const state = {
    loggedIn: !!(settings.get().serverUrl && tokenStore.load()),
    status: null,
    employeeName: '',
    receivedAt: 0,
    day: null,
    reminders: [],
    pendingActions: [],
    offline: false,
    problem: '',
    notice: null,
  };

  function getServerUrl() {
    return tentativeUrl || settings.get().serverUrl;
  }

  function snapshot() {
    const s = settings.get();
    const extras = deps.extras ? deps.extras() : {};
    return {
      loggedIn: state.loggedIn,
      serverUrl: s.serverUrl,
      insecure: !!validateServerUrl(s.serverUrl).insecure,
      loginName: s.loginName,
      secureStorage: tokenStore.persistent(),
      notificationsEnabled: s.notificationsEnabled,
      appVersion: extras.appVersion || '',
      openAtLogin: !!extras.openAtLogin,
      canAutoStart: !!extras.canAutoStart,
      status: state.status,
      statusLabel: state.status ? STATUS_LABELS[state.status.status] || state.status.status : 'Not Signed In',
      employeeName: state.employeeName || s.userName || '',
      receivedAt: state.receivedAt,
      day: state.day,
      reminders: state.reminders,
      pendingActions: state.pendingActions,
      pendingCount: queue.count(),
      offline: state.offline,
      problem: state.problem,
      notice: state.notice,
    };
  }

  function emit() {
    if (deps.onChange) deps.onChange(snapshot());
  }

  function setNotice(kind, text) {
    state.notice = { kind, text, at: now() };
  }

  function resetData() {
    state.status = null;
    state.day = null;
    state.reminders = [];
    state.pendingActions = [];
    state.receivedAt = 0;
    state.offline = false;
    state.problem = '';
  }

  /** The saved login stopped working: back to the login screen. */
  function handleAuthLost(message) {
    state.loggedIn = false;
    resetData();
    setNotice('error', message || 'Your session has ended. Please sign in again.');
    emit();
  }

  async function poll() {
    if (!state.loggedIn) return;
    if (polling) return polling;
    polling = (async () => {
      const results = await Promise.allSettled([workspace.getStatus(), workspace.getDay(), workspace.getReminders()]);
      const [s, d, r] = results;
      const auth = results.find((x) => x.status === 'rejected' && x.reason instanceof AuthError);
      if (auth) {
        handleAuthLost(auth.reason.message);
        return;
      }
      const net = results.some((x) => x.status === 'rejected' && x.reason instanceof NetworkError);
      state.offline = net;
      const other = results.find((x) => x.status === 'rejected' && !(x.reason instanceof NetworkError));
      state.problem = other ? (other.reason instanceof ApiError ? other.reason.message : 'Something went wrong while checking the server.') : '';
      if (s.status === 'fulfilled') {
        state.status = s.value.state || null;
        state.employeeName = (s.value.employee && s.value.employee.name) || state.employeeName;
        state.receivedAt = now();
        if (state.employeeName && state.employeeName !== settings.get().userName) settings.set({ userName: state.employeeName });
      }
      if (d.status === 'fulfilled') state.day = d.value.day || null;
      if (r.status === 'fulfilled') {
        state.reminders = Array.isArray(r.value.reminders) ? r.value.reminders : [];
        state.pendingActions = Array.isArray(r.value.pending_actions) ? r.value.pending_actions : [];
      }
      emit();
      if (r.status === 'fulfilled' && settings.get().notificationsEnabled && deps.onNewReminders) {
        const fresh = shown.fresh(state.reminders);
        for (const reminder of fresh) shown.add(reminder.id);
        if (fresh.length) deps.onNewReminders(fresh);
      }
    })();
    const done = () => {
      polling = null;
    };
    polling.then(done, done);
    return polling;
  }

  /** Try to send waiting actions. Safe to call often. */
  async function flushQueue() {
    if (!state.loggedIn || queue.count() === 0) return;
    if (flushing) return flushing;
    flushing = (async () => {
      const results = await queue.flush();
      for (const res of results) {
        const label = res.item.label || 'Your action';
        if (res.outcome === 'sent') setNotice('ok', `Sent now: ${label}. ${res.message}`.trim());
        else setNotice('error', `${label} was not accepted. ${res.message}`.trim());
      }
      if (results.length) await poll();
      emit();
    })();
    const done = () => {
      flushing = null;
    };
    flushing.then(done, done);
    return flushing;
  }

  const ACTIONS = {
    sign_in: () => workspace.signIn(),
    sign_out: () => workspace.signOut(),
    end_break: () => workspace.endBreak(),
    submit_update: (p) => workspace.submitUpdate(p.type, p.summary),
    skip_midday: (p) => workspace.skipMidday(p.choice),
    snooze: (p) => workspace.snooze(p.id, p.minutes),
    ack: (p) => workspace.ack(p.id),
  };

  /** Run one user action. Returns { ok, message, queued?, data? }. */
  async function perform(name, payload = {}) {
    const fn = ACTIONS[name];
    if (!fn) return { ok: false, message: 'Unknown action.' };
    const lock = name === 'submit_update' ? `${name}:${payload.type}` : name;
    if (inFlight.has(lock)) return { ok: false, message: 'Still saving. Please wait.' };
    if (!state.loggedIn) return { ok: false, message: 'Please sign in first.' };
    inFlight.add(lock);
    try {
      const result = await fn(payload);
      if (result.authLost) {
        handleAuthLost(result.message);
        return result;
      }
      if (result.queued) {
        emit();
      } else if (result.ok && name !== 'ack') {
        await poll();
      }
      return result;
    } finally {
      inFlight.delete(lock);
    }
  }

  /** Log in. Never stores the password. */
  async function login({ serverUrl, username, password, confirmInsecure }) {
    const check = validateServerUrl(serverUrl);
    if (!check.ok) return { ok: false, message: check.error };
    if (check.insecure && !confirmInsecure) {
      return { ok: false, needsConfirm: true, message: check.warning };
    }
    if (!username || !password) return { ok: false, message: 'Please type your user name and password.' };
    tentativeUrl = check.url;
    try {
      const who = await api.login(username, password);
      const previous = settings.get();
      const sameUser = previous.loginName && previous.loginName.toLowerCase() === username.toLowerCase() && previous.serverUrl === check.url;
      if (!sameUser && queue.count() > 0) queue.clear(); // never send one person's waiting actions as another person
      settings.set({ serverUrl: check.url, loginName: username, userName: who.name });
      tentativeUrl = null;
      state.loggedIn = true;
      state.notice = null;
      resetData();
      emit();
      await poll();
      await flushQueue();
      return { ok: true, message: 'Signed in.' };
    } catch (e) {
      tentativeUrl = null;
      if (e instanceof NetworkError) {
        return { ok: false, message: 'Could not reach the server. Check the address and your internet connection.' };
      }
      if (e instanceof ApiError || e instanceof AuthError) return { ok: false, message: e.message };
      throw e;
    }
  }

  async function logout() {
    const waiting = queue.count();
    const { serverConfirmed } = await api.logout();
    if (waiting > 0) queue.clear();
    state.loggedIn = false;
    resetData();
    state.notice = null;
    let text = serverConfirmed ? 'You are signed out.' : 'You are signed out on this computer. The server could not be reached to end the session there.';
    if (waiting > 0) text += ` ${waiting} unsent action${waiting === 1 ? ' was' : 's were'} discarded.`;
    setNotice('ok', text);
    emit();
    return { ok: true, message: text };
  }

  function setNotifications(enabled) {
    settings.set({ notificationsEnabled: !!enabled });
  }

  return { snapshot, setNotifications, poll, flushQueue, perform, login, logout, getServerUrl, handleAuthLost, emit, STATUS_LABELS };
}

module.exports = { createController, STATUS_LABELS };
