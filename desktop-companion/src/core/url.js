'use strict';

const LOCAL_HOSTS = new Set(['localhost', '127.0.0.1', '[::1]', '::1']);

/**
 * Check the Server URL the user typed.
 * Returns { ok, url, insecure, warning, error }.
 *  - url is normalised (no trailing slash, no path).
 *  - insecure is true when the address is plain http and not this computer.
 */
function validateServerUrl(input) {
  const raw = String(input == null ? '' : input).trim();
  if (!raw) return { ok: false, error: 'Please type the server address.' };
  let parsed;
  try {
    parsed = new URL(raw);
  } catch (e) {
    return { ok: false, error: 'This does not look like a web address. Example: https://hr.yourcompany.com' };
  }
  if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') {
    return { ok: false, error: 'The address must start with https:// (or http:// for this computer only).' };
  }
  if (parsed.username || parsed.password) {
    return { ok: false, error: 'Do not put a user name or password inside the address.' };
  }
  const host = parsed.hostname.toLowerCase();
  const isLocal = LOCAL_HOSTS.has(host);
  const insecure = parsed.protocol === 'http:' && !isLocal;
  const url = `${parsed.protocol}//${parsed.host}`;
  const result = { ok: true, url, insecure };
  if (insecure) {
    result.warning =
      'This connection is not secure. Your password and work data could be read by other people on the network. ' +
      'Only continue if your IT team told you to use this address.';
  }
  return result;
}

module.exports = { validateServerUrl };
