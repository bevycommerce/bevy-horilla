'use strict';

const { Notification } = require('electron');
const { notificationButtons } = require('../core/reminders');
const { clockFromIso } = require('../core/time');

const TITLE = 'BevyLoop';
const DUPLICATE_WINDOW_MS = 1500;

/**
 * Native notifications.
 * deps: { controller, showPopup(view), iconPath, platform, log }
 *
 * Buttons (Windows toast / macOS alert) are best effort: a plain click always
 * opens the popup. On Windows we also register Notification.handleActivation, which
 * can fire for a notification we no longer hold. It does not say WHICH notification
 * was used, so we only ever act on it when the per-notification event did not
 * already run; and then we do the safe thing (open the popup), never a guess.
 */
function createNotifier({ controller, showPopup, iconPath, platform = process.platform, log = () => {} }) {
  const live = new Map(); // keep references so notifications are not garbage collected
  let lastHandledAt = 0;

  function info(body) {
    if (!Notification.isSupported()) return;
    const n = new Notification({ title: TITLE, body: String(body), icon: iconPath });
    n.on('click', () => showPopup('main'));
    n.show();
  }

  async function runAction(reminder, action) {
    try {
      if (action === 'sign_in' || action === 'sign_out') {
        const result = await controller.perform(action);
        if (result.ok) {
          const state = result.data && result.data.state;
          const changed = result.data && result.data.changed !== false;
          const time = clockFromIso(state && (action === 'sign_in' ? (state.session_started_at || state.signed_in_at) : state.signed_out_at));
          if (changed && time) info(action === 'sign_in' ? `Signed in at ${time}` : `Signed out at ${time}`);
          else info(result.message);
          await controller.perform('ack', { id: reminder.id });
        } else {
          info(result.message);
        }
      } else if (action === 'skip_midday') {
        const result = await controller.perform('skip_midday', { choice: 'combine' });
        info(result.message);
        if (result.ok) await controller.perform('ack', { id: reminder.id });
      } else if (action === 'snooze') {
        const result = await controller.perform('snooze', { id: reminder.id, minutes: 15 });
        info(result.ok ? 'Reminder snoozed for 15 minutes.' : result.message);
      } else if (action === 'open_update') {
        showPopup('update');
      } else {
        showPopup('main');
      }
    } catch (e) {
      log('notification action failed', e && e.message);
      info('Something went wrong. Please open BevyLoop and try again.');
    }
  }

  function handle(reminder, type, index, buttons) {
    lastHandledAt = Date.now();
    live.delete(reminder.id);
    if (type === 'action' && Number.isInteger(index) && buttons[index]) {
      runAction(reminder, buttons[index].action);
    } else {
      showPopup('main'); // plain click
    }
  }

  function showReminder(reminder) {
    if (!Notification.isSupported()) return;
    const buttons = notificationButtons(reminder.kind);
    const n = new Notification({
      title: TITLE,
      body: String(reminder.message || ''),
      icon: iconPath,
      actions: buttons.map((b) => ({ type: 'button', text: b.text })),
      timeoutType: 'never',
    });
    n.on('click', () => handle(reminder, 'click', undefined, buttons));
    n.on('action', (details, legacyIndex) => {
      const index = details && Number.isInteger(details.actionIndex) ? details.actionIndex : legacyIndex;
      handle(reminder, 'action', index, buttons);
    });
    n.on('close', () => live.delete(reminder.id));
    live.set(reminder.id, n);
    n.show();
  }

  function init() {
    if (platform === 'win32' && typeof Notification.handleActivation === 'function') {
      Notification.handleActivation(() => {
        // Wait a moment: if the per-notification event ran, it already handled this.
        setTimeout(() => {
          if (Date.now() - lastHandledAt > DUPLICATE_WINDOW_MS) showPopup('main');
        }, 400);
      });
    }
  }

  return { showReminder, info, init };
}

module.exports = { createNotifier };
