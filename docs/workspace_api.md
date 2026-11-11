# Smart Employee Workspace API (v1)

Base path: `/api/workspace/v1/` (also reachable as `/api/v1/workspace/v1/` because Horilla mounts its API twice).

Used by the Desktop Companion. Any other client may use it the same way.

## Authentication

Uses Horilla's existing JWT API (the same one as the Horilla mobile app):

| Step | Request | Notes |
|---|---|---|
| Log in | `POST /api/auth/login/` `{ "username", "password" }` | Returns an access token (60 min) and a refresh token (30 days). Throttled (12/min). |
| Refresh | `POST /api/auth/refresh/` `{ "refresh" }` | Refresh tokens rotate: store the new one. |
| Log out | `POST /api/auth/logout/` `{ "refresh" }` | Blacklists the refresh token. Changing the password also revokes tokens. |

Send `Authorization: Bearer <access>` on every Workspace call.

## Common rules

- **Who:** the employee is always the logged-in user. Any `employee` / `employee_id` sent by a client is ignored.
- **Idempotency-Key:** every `POST`/`PATCH` that creates or changes attendance or updates must carry an `Idempotency-Key` header (8 to 64 characters: letters, digits, `_ - : .`). A repeated key returns the first answer with `"replayed": true` and does nothing again. Reusing a key for a different action returns `409 idempotency_conflict`. Keys are kept 7 days. Snooze and ack do not need a key.
- **Source:** send `X-Workspace-Client: desktop` from the desktop app; events are stored with `source=desktop` (otherwise `api`).
- **Errors:** `{ "ok": false, "code": "<machine_code>", "message": "<text safe to show>" }` with HTTP 400 (invalid), 401 (not logged in), 403 (not allowed: no employee profile, check-in disabled, IP or location rule), 404 (not found or not yours), 409 (conflict: duplicate, already sent, state does not allow it).
- **Times:** ISO 8601 with offset in the company time zone (`TIME_ZONE`, Asia/Dhaka). `work_date` is always separate from `submitted_at` / `recorded_at`.

## Attendance

### `GET status/`
```json
{
  "ok": true,
  "employee": {"id": 7, "name": "...", "photo": "...", "department_id": 3, "department": "Engineering", "job_position": "..."},
  "state": {
    "status": "not_signed_in | working | away | on_break | signed_out",
    "work_date": "2026-11-11",
    "attendance_id": 123,
    "signed_in_at": "2026-11-11T09:02:00+06:00",
    "signed_out_at": null,
    "worked_seconds": 3600,
    "timer_running": true,
    "break": null,
    "away_since": null,
    "server_time": "2026-11-11T10:02:00+06:00"
  },
  "break_reasons": [{"value": "prayer", "label": "Prayer"}],
  "correction_window_days": 30
}
```

### `POST sign-in/` and `POST sign-out/`
Body (optional): `{ "latitude": 23.8, "longitude": 90.4 }` (only needed when the company uses location rules).
Answer: `{ "ok": true, "changed": true, "message": "Signed in at 09:02.", "state": {...} }`.
`changed: false` means nothing was needed (already signed in / not signed in). Signing out while on a break ends the break first.
Company rules apply exactly as on the website: check-in disabled, IP restriction and geofencing give `403` with codes `disabled`, `ip_restricted`, `location_restricted`.
A Workspace sign-out marks that day valid for payroll (`WORKSPACE_AUTO_VALIDATE`); overtime pay still needs HR approval.

### `POST break/start/` `{ "reason", "note" }`, `POST break/end/`
The owner's break feature. The card and desktop app currently do not offer "start break" (`WORKSPACE_SHOW_BREAK=False`), but `break/end/` is used when a break was started from the header.

### `POST away/` `{ "away": true | false }`
Marks Away / back. Needs an open sign-in (else `409 not_signed_in`).

### `GET corrections/`, `POST corrections/`
GET lists the last N days (`window_days`, default 30): `{date, sign_in, sign_out, worked, missing_sign_out}`.
POST `{ "date": "2026-11-10", "sign_in": "09:00", "sign_out": "18:00" }` (either time may be omitted). Saved immediately, no approval. Rules: not in the future, within the window, sign out after sign in (night shifts may end the next day), not while a Horilla attendance request for that day is pending. Every change is written to an append-only log with old and new values, who, when and source.

## Daily Updates

### `GET updates/?date=YYYY-MM-DD` (default today)
```json
{"ok": true, "day": {
  "work_date": "2026-11-11", "midday": null, "eod": null, "combined": null, "skip": "combine",
  "can_submit_midday": false, "can_skip_midday": true, "can_submit_eod": true, "can_submit_combined": true,
  "recommend_combined": true, "midday_pending_later": false, "carry_forward": ""
}}
```
Clients must decide what to show only from these flags.

### `POST updates/`
`{ "date"?: "...", "type": "midday" | "eod" | "combined", "summary": "...", "completed"?, "ongoing"?, "blockers"? }`
`201` with the saved update. `409` codes: `duplicate` (already sent this type), `combined_exists`, `separate_exists`. Late and backdated flags are set by the server.

### `PATCH updates/<id>/`
Edit your own update (same text fields). The previous version is kept; `404` for someone else's update.

### `POST updates/midday-skip/` `{ "date"?, "choice": "later" | "combine" }`
Stores the choice only (no update is created). Stops Midday reminders for that day; EOD and Sign Out reminders continue.

## Reminders

### `GET reminders/`
```json
{"ok": true,
 "reminders": [{"id": 51, "kind": "sign_in", "work_date": "2026-11-11", "message": "...", "due_at": "...", "created_at": "...", "actions": ["sign_in", "snooze"]}],
 "pending_actions": [{"kind": "midday", "label": "Write or skip your Midday update", "work_date": "2026-11-11"}],
 "snooze_choices": [15, 30]}
```
Only reminders whose action is still needed are returned. Kinds: `sign_in`, `sign_in_followup`, `midday`, `eod`, `sign_out`.

### `POST reminders/<id>/snooze/` `{ "minutes": 15 | 30 }` and `POST reminders/<id>/ack/`
Snooze hides that reminder kind for the day until the time passes, then it fires once more if still needed.

## Settings that change API behaviour

| Setting | Default | Effect |
|---|---|---|
| `WORKSPACE_CORRECTION_WINDOW_DAYS` | 30 | Fix My Times window |
| `WORKSPACE_AUTO_VALIDATE` | True | Workspace sign-outs and corrections count for payroll immediately |
| `WORKSPACE_SHOW_BREAK` | False | Show the start-break button in the card and desktop app |
| `WORKSPACE_UPDATE_BACKDATE_DAYS` | 30 | How far back updates can be sent |
| `WORKSPACE_MIDDAY_LATE_AFTER_MINUTES` | 60 | Grace after the shift midpoint before a Midday note counts as late |
| `WORKSPACE_REMINDERS` | see `workspace_reminders/conf.py` | Reminder timings, repeats, snooze choices, on/off |
| `WORKSPACE_IDEMPOTENCY_DAYS` | 7 | How long Idempotency-Keys are remembered |
| `WORKSPACE_ADAPTER` | `workspace_attendance.adapters.horilla.HorillaAdapter` | Connects the modules to the HR system |
