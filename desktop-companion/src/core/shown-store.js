'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { localDateKey } = require('./time');

/**
 * Remembers which reminder ids already produced a notification today,
 * saved to disk so a restart does not notify again.
 * File format: { date: "YYYY-MM-DD", ids: [1,2] }. A new day starts empty.
 */
function createShownStore({ filePath, fsImpl = fs, today = () => localDateKey() }) {
  let state = { date: today(), ids: [] };
  try {
    const parsed = JSON.parse(fsImpl.readFileSync(filePath, 'utf8'));
    if (parsed && Array.isArray(parsed.ids) && typeof parsed.date === 'string') state = parsed;
  } catch (e) {
    /* first run */
  }

  function rollover() {
    const day = today();
    if (state.date !== day) state = { date: day, ids: [] };
  }

  function save() {
    fsImpl.mkdirSync(path.dirname(filePath), { recursive: true });
    fsImpl.writeFileSync(filePath, JSON.stringify(state));
  }

  return {
    has(id) {
      rollover();
      return state.ids.includes(id);
    },
    add(id) {
      rollover();
      if (!state.ids.includes(id)) {
        state.ids.push(id);
        save();
      }
    },
    /** Reminders we have not shown yet. */
    fresh(reminders) {
      rollover();
      return reminders.filter((r) => !state.ids.includes(r.id));
    },
  };
}

module.exports = { createShownStore };
