'use strict';

const { ipcMain, shell, app } = require('electron');
const { validateServerUrl } = require('../core/url');

const UPDATE_TYPES = new Set(['midday', 'eod', 'combined']);
const SKIP_CHOICES = new Set(['later', 'combine']);
const MAX_NOTE = 5000;
const MAX_PART = 3000;

function isString(v, max) {
  return typeof v === 'string' && v.length <= max;
}

/**
 * The only door between the window and the app.
 * The window never sees tokens; every input is checked here.
 */
function registerIpc({ controller, popup, setLoginItem, refreshAndFlush }) {
  const fromPopup = (event) => event.sender === popup.win.webContents;

  function handle(channel, fn) {
    ipcMain.handle(channel, async (event, ...args) => {
      if (!fromPopup(event)) return { ok: false, message: 'Not allowed.' };
      return fn(...args);
    });
  }

  handle('app:get-snapshot', () => controller.snapshot());

  handle('app:refresh', async () => {
    await refreshAndFlush();
    return controller.snapshot();
  });

  handle('app:network-online', async () => {
    await refreshAndFlush();
    return { ok: true };
  });

  handle('auth:login', async (input) => {
    if (!input || typeof input !== 'object') return { ok: false, message: 'Invalid request.' };
    const { serverUrl, username, password, confirmInsecure } = input;
    if (!isString(serverUrl, 300) || !isString(username, 200) || !isString(password, 500)) {
      return { ok: false, message: 'Please fill in all fields.' };
    }
    return controller.login({ serverUrl, username: username.trim(), password, confirmInsecure: confirmInsecure === true });
  });

  handle('url:check', (value) => {
    if (!isString(value, 300)) return { ok: false, error: 'Please type the server address.' };
    return validateServerUrl(value);
  });

  handle('auth:logout', () => controller.logout());

  handle('action:run', async (name, payload) => {
    if (!isString(name, 40)) return { ok: false, message: 'Invalid request.' };
    const p = payload && typeof payload === 'object' ? payload : {};
    switch (name) {
      case 'sign_in':
      case 'sign_out':
      case 'end_break':
        return controller.perform(name);
      case 'submit_update': {
        if (!UPDATE_TYPES.has(p.type) || !isString(p.summary, MAX_NOTE)) {
          return { ok: false, message: 'Please check your note.' };
        }
        if (!p.summary.trim()) return { ok: false, message: 'Please write something first.' };
        return controller.perform('submit_update', { type: p.type, summary: p.summary.trim() });
      }
      case 'edit_update': {
        if (!Number.isInteger(p.id) || p.id <= 0) return { ok: false, message: 'Please check your note.' };
        if (!isString(p.summary, MAX_NOTE) || !isString(p.completed == null ? '' : p.completed, MAX_PART)
          || !isString(p.ongoing == null ? '' : p.ongoing, MAX_PART) || !isString(p.blockers == null ? '' : p.blockers, MAX_PART)) {
          return { ok: false, message: 'Your note is too long.' };
        }
        if (!p.summary.trim()) return { ok: false, message: 'Please write something first.' };
        return controller.perform('edit_update', {
          id: p.id, summary: p.summary.trim(), completed: p.completed || '', ongoing: p.ongoing || '', blockers: p.blockers || '',
        });
      }
      case 'delete_update':
        if (!Number.isInteger(p.id) || p.id <= 0) return { ok: false, message: 'Invalid request.' };
        return controller.perform('delete_update', { id: p.id });
      case 'skip_midday':
        if (!SKIP_CHOICES.has(p.choice)) return { ok: false, message: 'Invalid choice.' };
        return controller.perform('skip_midday', { choice: p.choice });
      default:
        return { ok: false, message: 'Unknown action.' };
    }
  });

  handle('pending:retry', async () => {
    await refreshAndFlush();
    return controller.snapshot();
  });

  handle('settings:save', (patch) => {
    if (!patch || typeof patch !== 'object') return { ok: false, message: 'Invalid request.' };
    const result = { ok: true, message: '' };
    if (typeof patch.notificationsEnabled === 'boolean') controller.setNotifications(patch.notificationsEnabled);
    if (typeof patch.openAtLogin === 'boolean') {
      const r = setLoginItem(patch.openAtLogin);
      if (!r.ok) {
        result.ok = false;
        result.message = r.message;
      }
    }
    controller.emit();
    return result;
  });

  handle('shell:open-editor', () => {
    const url = validateServerUrl(controller.snapshot().serverUrl);
    if (!url.ok) return { ok: false, message: 'Set the server address first.' };
    shell.openExternal(`${url.url}/daily-updates/`);
    return { ok: true };
  });

  handle('window:set-pinned', (value) => {
    popup.setPinned(value === true);
    return { ok: true, pinned: popup.isPinned() };
  });

  handle('window:hide', () => {
    popup.hide();
    return { ok: true };
  });

  handle('app:version', () => app.getVersion());
}

module.exports = { registerIpc };
