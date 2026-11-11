'use strict';

const fs = require('node:fs');
const path = require('node:path');

// windowX / windowY: where the person last dragged the window (NO_POSITION = not moved yet)
const NO_POSITION = -99999;
const DEFAULTS = { serverUrl: '', notificationsEnabled: true, userName: '', loginName: '', windowX: NO_POSITION, windowY: NO_POSITION };
const num = (v) => (typeof v === 'number' && Number.isFinite(v) ? Math.round(v) : NO_POSITION);

function createSettingsStore({ filePath, fsImpl = fs }) {
  let data = { ...DEFAULTS };
  try {
    const parsed = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'));
    if (parsed && typeof parsed === 'object') {
      data = {
        serverUrl: typeof parsed.serverUrl === 'string' ? parsed.serverUrl : '',
        notificationsEnabled: parsed.notificationsEnabled !== false,
        userName: typeof parsed.userName === 'string' ? parsed.userName : '',
        loginName: typeof parsed.loginName === 'string' ? parsed.loginName : '',
        windowX: num(parsed.windowX),
        windowY: num(parsed.windowY),
      };
    }
  } catch (e) {
    /* first run */
  }
  return {
    get: () => ({ ...data }),
    set(patch) {
      for (const key of Object.keys(DEFAULTS)) {
        if (key in patch && typeof patch[key] === typeof DEFAULTS[key]) data[key] = patch[key];
      }
      fsImpl.mkdirSync(path.dirname(filePath), { recursive: true });
      fsImpl.writeFileSync(filePath, JSON.stringify(data));
      return { ...data };
    },
  };
}

module.exports = { createSettingsStore, NO_POSITION };
