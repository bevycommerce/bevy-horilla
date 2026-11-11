'use strict';

const SNOOZE = { text: 'Snooze 15 min', action: 'snooze' };

/** Buttons for each kind of reminder. `action` is what the app does when pressed. */
function notificationButtons(kind) {
  switch (kind) {
    case 'sign_in':
    case 'sign_in_followup':
      return [{ text: 'Sign In Now', action: 'sign_in' }, SNOOZE];
    case 'sign_out':
      return [{ text: 'Sign Out Now', action: 'sign_out' }, SNOOZE];
    case 'midday':
      return [{ text: 'Skip Midday (combine)', action: 'skip_midday' }, SNOOZE];
    case 'eod':
      return [{ text: 'Write update', action: 'open_update' }, SNOOZE];
    default:
      return [{ text: 'Open', action: 'open' }, SNOOZE];
  }
}

module.exports = { notificationButtons };
