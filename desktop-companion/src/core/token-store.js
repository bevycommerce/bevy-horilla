'use strict';

const fs = require('node:fs');
const path = require('node:path');

/**
 * Keeps the refresh token on disk, encrypted with the operating system
 * (Electron safeStorage: Windows DPAPI / macOS Keychain).
 * If encryption is not available the token is kept in memory only:
 * nothing is ever written to disk in plain text.
 *
 * Injectable: { filePath, safeStorage, fsImpl }.
 * safeStorage needs isEncryptionAvailable(), encryptString(str)->Buffer, decryptString(Buffer)->str.
 */
function createTokenStore({ filePath, safeStorage, fsImpl = fs }) {
  let memoryToken = null;

  function canEncrypt() {
    try {
      return !!(safeStorage && safeStorage.isEncryptionAvailable());
    } catch (e) {
      return false;
    }
  }

  function writeFile(data) {
    fsImpl.mkdirSync(path.dirname(filePath), { recursive: true });
    fsImpl.writeFileSync(filePath, data);
  }

  return {
    /** True when the token survives an app restart. */
    persistent() {
      return canEncrypt();
    },
    save(refreshToken) {
      memoryToken = refreshToken;
      if (canEncrypt()) {
        const encrypted = safeStorage.encryptString(refreshToken);
        writeFile(JSON.stringify({ v: 1, data: Buffer.from(encrypted).toString('base64') }));
      }
    },
    load() {
      if (memoryToken) return memoryToken;
      if (!canEncrypt()) return null;
      try {
        const parsed = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'));
        if (!parsed || !parsed.data) return null;
        memoryToken = safeStorage.decryptString(Buffer.from(parsed.data, 'base64'));
        return memoryToken;
      } catch (e) {
        return null;
      }
    },
    clear() {
      memoryToken = null;
      try {
        fsImpl.rmSync(filePath, { force: true });
      } catch (e) {
        /* nothing to remove */
      }
    },
  };
}

module.exports = { createTokenStore };
