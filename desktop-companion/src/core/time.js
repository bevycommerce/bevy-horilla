'use strict';

function pad(n) {
  return String(n).padStart(2, '0');
}

/** 3725 -> "01:02:05". Bad or negative input gives "00:00:00". */
function formatHMS(totalSeconds) {
  let s = Math.floor(Number(totalSeconds));
  if (!Number.isFinite(s) || s < 0) s = 0;
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${pad(h)}:${pad(m)}:${pad(s % 60)}`;
}

/**
 * Seconds to show on the timer. The server value is the truth at the moment
 * the answer arrived; we only add local time while the server says the timer runs.
 */
function currentWorkedSeconds(status, receivedAtMs, nowMs) {
  if (!status) return 0;
  const base = Number(status.worked_seconds) || 0;
  if (!status.timer_running) return base;
  const extra = Math.max(0, Math.floor((nowMs - receivedAtMs) / 1000));
  return base + extra;
}

/**
 * "2026-11-11T09:02:33+06:00" -> "09:02". The server already sends its own
 * local time, so we read the clock digits as written and do no zone conversion.
 */
function clockFromIso(iso) {
  if (typeof iso !== 'string') return '';
  const m = /T(\d{2}):(\d{2})/.exec(iso);
  return m ? `${m[1]}:${m[2]}` : '';
}

/** Local calendar day of this computer, "YYYY-MM-DD". */
function localDateKey(date) {
  const d = date || new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

module.exports = { formatHMS, currentWorkedSeconds, clockFromIso, localDateKey };
