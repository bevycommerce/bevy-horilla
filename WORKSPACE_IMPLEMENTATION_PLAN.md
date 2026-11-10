# Smart Employee Workspace - Implementation Plan

Status: Phase 0 (planning) complete as far as possible without a shell on the developer PC.
Last updated: 2026-11-10 (Asia/Dhaka).
Author: Claude (Opus), lead architect.

This file records verified facts about the existing Horilla code and the design decisions that
implementation must follow. Anyone resuming the work (human or Sonnet subagent) must read this
file and WORKSPACE_PROGRESS.md first.

---

## 1. Verified baseline

| Item | Verified value |
|---|---|
| Upstream | github.com/horilla/horilla-hr, branch `2.0` |
| Local base commit | `bba4b37bb4538ec1b9f149d10a3def64fc541c7a` (5 Nov 2026, "Merge dev/v2.0 into 2.0") |
| Git index | Byte-identical to the base commit. Nothing has ever been staged or committed locally. All custom work exists only as uncommitted working-tree files. |
| Django / DB / cache | Django 5.2, PostgreSQL 16, Redis 7 (cache only, via django-redis) |
| Scheduler | APScheduler via `python manage.py run_scheduler`, one dedicated `scheduler` container, `DjangoJobStore`, `max_instances=1`, `coalesce=True`. Jobs register through `horilla/scheduling.py::register_job`. No Celery. |
| API auth | DRF + SimpleJWT. `horilla_api.authentication.TenantScopedJWTAuthentication`. Access token 60 min, refresh 30 days, rotation + blacklist, password change revokes tokens. Endpoints: `/api/auth/login/`, `/api/auth/refresh/`, `/api/auth/logout/`. Login throttle scope `login` (12/min). |
| Existing attendance API | `/api/attendance/clock-in/`, `/api/attendance/clock-out/`, `/api/mobile/home/` (built for the Horilla mobile app) |
| Notifications | django-notifications, DB storage, navbar bell tray. No websockets / Channels. |
| Home routing | `/` -> `base.views.home`: analytics roles -> `dashboard`, everyone else -> `ess-dashboard` (`/my-dashboard/`) |
| Time zone | `TIME_ZONE = env("TIME_ZONE", default="Asia/Kolkata")`, `USE_TZ = True`. No `.env` file exists in the project root and `docker-compose.yml` does not set `TIME_ZONE`, so the running value is `Asia/Kolkata`. |

### Custom changes that must be preserved (found by file date, after the 4 Nov clone)

- `attendance/models.py` (AttendanceBreak, EmployeePresence), `attendance/urls.py`, `attendance/sidebar.py`
- `attendance/views/break_in_out.py` (break_start, break_end, break_log, set_status)
- `attendance/templates/attendance/components/in_out_component.html`, `attendance/templates/attendance/break_log.html`
- `attendance/templatetags/breakfilters.py`
- `attendance/migrations/0014_attendancebreak.py` to `0017_alter_attendancebreak_reason.py`
- `expense/` (whole new app, incl. `migrations/0001_initial.py`)
- `leave/approvals.py`, `leave/models.py`, `leave/views.py`, `leave/urls.py`, `leave/sidebar.py`, `leave/migrations/0013_leaveapprover.py`, leave templates (approver popup, approver picker, my approvals, user requests, request form)
- `recruitment/filters.py` (search by email)
- `horilla/settings/base.py` (expense added, project removed from sidebar), `horilla/urls.py`
- Untracked local files: `backup.sql`, `seed_candidates.py`, `setup_leave_test_data.py`, `horilla/settings/base.py.backup`

The date-based list may be incomplete. The first Phase 0 step on the PC is a full `git status` (see section 9).

---

## 2. Verified Horilla attendance and payroll internals

1. **Sign in** (`attendance/views/clock_in_out.py`): `clock_in()` (web) and `ClockInAPIView` (API) resolve shift and attendance date (night shifts use a noon-to-noon window), then call `clock_in_attendance_and_activity()`, which creates or reuses the day's `Attendance` and opens an `AttendanceActivity`. IP restriction (`AttendanceAllowedIP`) and geofencing are enforced when enabled.
2. **Sign out**: `clock_out_attendance_and_activity()` closes the activity, sums durations into `attendance_worked_hour`, runs `overtime_calculation()`, then sets `attendance_validated = attendance_validate(attendance)`.
3. **Auto validation rule** (`attendance/views/views.py::attendance_validate`): validated only if worked time is <= `AttendanceValidationCondition.validation_at_work` (default 09:00) and >= the optional minimum. Longer days stay unvalidated until HR validates them.
4. **Payroll reads only validated attendance**: `payroll/methods/payslip_calc.py` and `payroll/methods/methods.py::get_attendance()` filter `attendance_validated=True`. `payroll/methods/payroll_run.py` lists unvalidated days and unapproved overtime as items needing HR action.
5. **Overtime pay** additionally requires `attendance_overtime_approve=True` (HR approval). Separate from validation.
6. **Work records**: `attendance/signals.py::update_work_record_from_attendance` sets `WorkRecords` to `CONF` ("Validate the attendance") when unvalidated, otherwise FDP / HDP / ABS. Payroll and reports read work records.
7. **Corrections today**: employees submit an attendance request, which sets `is_validate_request=True` and forces `attendance_validated=False`. HR approves through `approve_validate_attendance_request()` (`attendance/views/requests.py`). That function shows the safe correction sequence: update fields, sync the matching `AttendanceActivity`, set validated, re-run `late_come()` and `early_out()`.
8. **Breaks (custom)**: starting a break closes the running activity and ending it opens a new one, so break time is excluded from worked time. The logic currently lives inside the request-bound views in `break_in_out.py`.
9. **History**: `Attendance` and `AttendanceActivity` already use `HorillaAuditLog` (simple_history).

---

## 3. Design decisions

**D1. Single source of truth.** Workspace never stores its own attendance times. Sign in/out always goes through Horilla's `clock_in_attendance_and_activity()` / `clock_out_attendance_and_activity()`. Workspace tables only hold metadata (events, idempotency, audit, updates, reminders).

**D2. Payroll compatibility, narrowly scoped (resolves the validation conflict).**
- Requirement: Workspace sign in/out and self-corrections are effective immediately with no approval.
- Implementation: after a Workspace sign-out or self-correction, the service sets `attendance_validated=True` on that single `Attendance` row and records it in `WorkspaceAttendanceMeta` (one-to-one: `managed_by_workspace`, `last_source`, `last_corrected_at`). The global `attendance_validate()` rule and HR's validation pages are untouched for every other record.
- Overtime: `attendance_overtime_approve` stays an HR decision (unchanged). Workspace records count for base pay immediately. Overtime pay still needs HR approval, as today. This is disclosed in the UI and docs.
- Controlled by `WORKSPACE_AUTO_VALIDATE = True` in settings, so the policy is one switch, not scattered code.
- Phase 1 must include a test that builds a payslip for a Workspace-created day and confirms it is counted exactly as an HR-validated day would be.

**D3. Concurrency and duplicates.** Every attendance action runs in `transaction.atomic()` with `select_for_update()` on the employee's `Employee` row, so two simultaneous clicks are serialized. A state check refuses "sign in while working" / "sign out while not working" with a friendly no-op response. Every mutating API call requires an `Idempotency-Key` header. `WorkspaceIdempotencyKey(employee, key unique per employee, action, response_json, created_at)` replays the stored response for a repeated key. Keys expire after 7 days (cleanup job).

**D4. Two timestamps.** `WorkspaceAttendanceEvent(employee, attendance, action, reported_time, recorded_at=server now, source=web|desktop|api, idempotency_key)` is written for every sign in, sign out, break start/end and correction. `reported_time` is the time the employee says it happened. `recorded_at` is the server clock.

**D5. Fix My Times.**
- Window: `WORKSPACE_CORRECTION_WINDOW_DAYS = 30` (calendar days back from today, in company time zone). No future times. Sign out must be after sign in (night shifts allowed through Horilla's own date rules).
- Existing record: update `attendance_clock_in`/`out` (+ dates), the first activity's start and the last activity's end. Break segments in between are kept. A correction that would cut through an existing break is rejected with a clear message.
- Missing record: create `Attendance` + one `AttendanceActivity` using the adapter's shift lookup.
- Then recompute worked hours (sum of activities), overtime (`overtime_calculation`), `late_come()` / `early_out()`, set validated per D2, save (signals update work records).
- Does not create or touch Horilla attendance requests.

**D6. Immutable audit.** `AttendanceCorrectionLog(employee, attendance, work_date, field, old_value, new_value, reported_time, recorded_at, source, actor_user, idempotency_key)`. `save()` refuses updates to existing rows, `delete()` raises, admin is read-only. Horilla's existing history tables continue to record too.

**D7. Breaks and Away.** The custom break and Away logic is extracted from `break_in_out.py` views into plain functions in a new `attendance/services/breaks.py` (same behaviour), and the existing views call those functions. This is the only change to custom files in Phase 1 and must be a pure refactor, verified by tests before and after. Workspace calls the same functions.

**D8. Workspace statuses.** Computed by the adapter from Horilla data: Not Signed In, Working (open activity), On Break (open `AttendanceBreak`), Away (`EmployeePresence.away_since` newer than last activity/break end), Signed Out (attendance with clock out and no open activity).

**D9. Daily Updates data model** (`daily_updates`):
- `DailyUpdate(employee, work_date, update_type: MIDDAY|EOD|COMBINED, summary, completed, ongoing, blockers, source, submitted_at, last_edited_at, revision_count, is_late)`.
- DB unique constraint `(employee, work_date, update_type)`. The service also refuses MIDDAY or EOD when a COMBINED exists for that date and the reverse (checked under a row lock), so a combined note is never split or duplicated.
- `DailyUpdateRevision(update, revision_number, summary, completed, ongoing, blockers, edited_at, edited_by, source)`: append-only. Editing creates a revision with the old content. The card shows "Edited".
- `MiddaySkip(employee, work_date unique, choice: LATER|COMBINE, created_at, source)`. Not an update. Changing the choice later is allowed and logged.
- Late: a Midday note submitted after the shift's midpoint plus a grace period (`WORKSPACE_MIDDAY_LATE_AFTER_MINUTES`) or after a LATER skip. Backdated: `submitted_at` local date is after `work_date`.
- "Write later" notes never expire. EOD screen offers: regular EOD, the pending Midday note, or the single Combined editor (if COMBINE was chosen). "Copy unfinished items" copies Midday `ongoing` into the EOD editor on demand only.

**D10. Company-wide visibility with a field whitelist.** One `safe_employee_card(employee)` function returns only: display name, profile photo URL, department name, job position name. Dashboard querysets use `.values()` / explicit serializers built only from that function plus attendance times and update text. No salary, contact info, contracts, documents or HR notes are ever loaded into these views. A privacy test asserts the rendered HTML and API JSON contain none of a list of sensitive field values. A banner says: "Work updates you submit are visible to everyone in the company."

**D11. Reminder engine** (`workspace_reminders`):
- One job: `register_job(run_reminders, "interval", job_id="workspace_reminders.run", minutes=2, misfire_grace_time=300)`.
- For each active employee with an employee profile, the adapter returns today's shift window (start, end, midpoint) or None for weekly off, holiday, company leave or approved leave.
- Rules (all in `WORKSPACE_REMINDERS` setting): sign-in at start; follow-up at start+30m if still missing; midday at midpoint unless a Midday update or MiddaySkip exists; EOD at end-30m unless EOD/COMBINED exists; sign-out at end if still working. Max repeats per kind per day (default 2, 30 min apart).
- Duplicate safety: `ReminderDelivery(employee, work_date, kind, attempt)` with a DB unique constraint. The job inserts the row first (`get_or_create`) and only sends when it created it, so even two scheduler processes cannot double-send.
- `ReminderSnooze(employee, work_date, kind, until)`: 15 or 30 minutes. Stored in DB. No Redis locks needed.
- Delivery: (1) `notify.send` into the existing bell, (2) Pending Actions list computed live on the homepage, (3) desktop app pulls `/api/workspace/v1/reminders/` every 60 s and shows native notifications, (4) browser fallback: the Workspace card uses the Web Notification API only while a portal tab is open, if the user grants permission.

**D12. API** at `/api/workspace/v1/`, auth `TenantScopedJWTAuthentication` (same tokens as mobile). The employee is always `request.user.employee_get`. No endpoint accepts an employee id from the client.

| Method | Path | Purpose |
|---|---|---|
| GET | `status/` | status, timer start, worked seconds, break state, pending actions, server time |
| POST | `sign-in/`, `sign-out/` | attendance actions (Idempotency-Key required) |
| POST | `break/start/`, `break/end/` | custom break feature |
| POST | `away/` | set or clear Away |
| GET/POST | `corrections/` | list recent days / submit Fix My Times |
| GET/POST | `updates/` , PATCH `updates/<id>/` | list today's updates / submit / edit |
| POST | `updates/midday-skip/` | choice LATER or COMBINE |
| GET | `reminders/` | due reminders for desktop |
| POST | `reminders/<id>/snooze/` | 15 or 30 |
| POST | `reminders/<id>/ack/` | mark shown |

Documented in `docs/workspace_api.md` and visible in the existing drf-yasg `/api/docs/`.

**D13. Desktop Companion: Electron.**

| Criterion | Electron | Tauri v2 |
|---|---|---|
| Tray (Windows) / menu bar (macOS) | Yes (`Tray`) | Yes |
| Notification action buttons on desktop | macOS: `actions` (app must be signed, alert style). Windows: toast actions supported, protocol activation | Official plugin: actions are essentially mobile-only, desktop shows no buttons |
| Secure token storage | `safeStorage` (Windows DPAPI, macOS Keychain) | Stronghold / keyring plugins |
| Start at login | `app.setLoginItemSettings` | autostart plugin |
| Packaging | electron-builder (NSIS for Windows, dmg for macOS) | built-in bundler |
| Size / memory | Larger (about 80 to 120 MB installed) | Much smaller |
| Fit with team skills | JavaScript only | Needs Rust toolchain |

Decision: Electron, because desktop notification buttons are a core requirement. Notification buttons must still be tested on the real Windows PC before being called verified.

Desktop behaviour: login via `/api/auth/login/`; refresh token stored with `safeStorage`; password never stored; server URL set on first run and in Settings (no default production URL); poll `status/` and `reminders/` every 60 s; every action shows "Saving..." until the server answers. Offline: show "Not saved", keep the action with its original Idempotency-Key and click time, retry automatically when online and on the Retry button; the server applies it once.

**D14. Adapter layer.** `workspace_attendance/adapters/base.py` defines the interface; `workspace_attendance/adapters/horilla.py` implements it. Setting `WORKSPACE_ADAPTER = "workspace_attendance.adapters.horilla.HorillaAdapter"`. Interface: `get_employee(user)`, `get_shift_window(employee, date)`, `is_day_off(employee, date)`, `get_status(employee)`, `sign_in(...)`, `sign_out(...)`, `start_break(...)`, `end_break(...)`, `set_away(...)`, `correct_times(...)`, `safe_employee_card(employee)`, `departments()`. Only this file imports Horilla models.

**D15. Time zone.** Horilla stores clock times as wall-clock `TimeField`s in `TIME_ZONE` and breaks as UTC `DateTimeField`s. Workspace must use the same zone as Horilla, so it uses `django.utils.timezone.localtime()` and `settings.TIME_ZONE` and never its own separate zone. Moving the company to `Asia/Dhaka` means setting `TIME_ZONE=Asia/Dhaka` in the environment (configuration only, no code change, no data conversion). Effect on existing rows: stored wall-clock times stay as recorded (India time, 30 minutes behind Dhaka); UTC datetimes display 30 minutes later. Needs the owner's decision (see section 8).

---

## 4. New modules and files

```
workspace_attendance/   adapters/, services.py, models.py (Meta, Event, CorrectionLog, IdempotencyKey),
                        views.py (HTMX card, Fix My Times), api/ (DRF views, serializers, urls), templates/, tests/
daily_updates/          models.py, services.py, views.py, sidebar.py (top-level "Daily Updates"), templates/, api/, tests/
workspace_reminders/    models.py (ReminderDelivery, ReminderSnooze), engine.py, scheduler.py, api/, tests/
attendance/services/breaks.py   (pure refactor of custom break logic, D7)
desktop-companion/      Electron app (main/, renderer/, package.json, electron-builder config, README.md)
docs/workspace_api.md
```

Edits to existing files (kept minimal, each listed in WORKSPACE_PROGRESS.md):
- `horilla/settings/base.py`: add 3 apps to INSTALLED_APPS, `daily_updates` to SIDEBARS, `WORKSPACE_*` settings.
- `horilla/urls.py` and `horilla_api/urls.py`: include new url modules.
- ESS dashboard and analytics dashboard templates: include the My Workspace card at the top.
- `attendance/views/break_in_out.py`: call the extracted service functions (D7).
- `base/management/commands/run_scheduler.py`: only if it needs to import the new scheduler module (check `_load_job_modules`).

---

## 5. Phases and exit criteria

| Phase | Scope | Exit criteria |
|---|---|---|
| 0 | Safety, git checkpoint, disk check, this plan | Branch `feature/smart-workspace` created from the current working tree; baseline test run recorded |
| 1 | Workspace attendance: card, sign in/out, timer, Break/Away, Fix My Times, audit, idempotency | Tests in section 6 for Phase 1 pass; payroll compatibility test passes; existing attendance and payroll tests still pass |
| 2 | Daily Updates + company dashboard | All Midday/Skip/Combined/EOD tests pass; privacy test passes |
| 3 | Reminder engine | Reminder tests pass, incl. double-run of the job |
| 4 | Workspace API + docs | API permission, idempotency, token expiry tests pass |
| 5 | Windows desktop app | Manual test checklist on the Windows PC completed and recorded |
| 6 | macOS | Config + signing docs; marked "not tested" until a Mac is available |
| 7 | Full QA + docs incl. MODULE_INTEGRATION_GUIDE.md | Full test suite run recorded in WORKSPACE_TEST_REPORT.md |

---

## 6. Required tests (mapped to phases)

- Phase 1: duplicate sign in, duplicate sign out, simultaneous requests (threaded test with a real PostgreSQL DB), idempotency replay, sign out with no sign in, self-correction, 30-day limit and boundary day, future time rejected, audit log immutability, break and Away compatibility, missing events, payroll and overtime compatibility, date-boundary and night-shift behaviour.
- Phase 2: midday submit, skip LATER, skip COMBINE, late midday, combined single record, duplicate update prevention, combined vs separate conflict, edit creates revision, company-wide visibility, restricted-field privacy.
- Phase 3: each reminder kind, stop after action, skip stops only midday, snooze 15/30, weekly off / holiday / leave exclusions, duplicate scheduler execution, restart safety.
- Phase 4: unauthenticated 401, other employee's data impossible, client-supplied employee id ignored, input validation, token expiry and refresh, logout revocation, offline retry with same key.
- Phase 5 (manual, Windows): login, tray, popup, sign in/out without browser, notification buttons, offline then online, start at login, installer and uninstall.

All results go to WORKSPACE_TEST_REPORT.md with one of: Implemented, Tested successfully, Partially tested, Not tested (reason).

---

## 7. Model routing

The environment supports subagents with explicit model selection. Opus orchestrates and reviews; routine implementation tasks are delegated to Sonnet subagents one at a time per shared area (never two agents editing the same files or migrations). Opus reviews: D2 payroll code, D3 concurrency, D6 audit, all migrations, API permissions, token handling in the desktop app.

---

## 8. Decisions needed from the owner

1. Time zone (D15): is the data currently in the local database test data? If yes, switch `TIME_ZONE` to `Asia/Dhaka` now with no conversion. If it is real data, a separate, reviewed conversion plan is needed first.
2. IP restriction / geofencing: default is to obey them exactly as the website does (desktop sign-in is refused when the PC is outside the allowed network or location). Change only if the owner says so.

## 9. Blockers

- **Disk space (blocks Phase 0 completion and all later phases on the PC).** The command-line environment on the developer PC needs up to 17 GB free on C: and cannot start. Without it: no `git status`, no git branch checkpoint, no Docker, no migrations, no test runs, no Electron build. Owner action: free about 20 GB on C:, then tell Claude.
- First commands once the shell works (read-only first, then the checkpoint):
  1. `git status --porcelain=v1 -uall` and `git diff --stat`
  2. Add `backup.sql`, `*.backup`, `.env`, `seed_candidates.py`, `setup_leave_test_data.py` to `.git/info/exclude` (local only, never committed)
  3. `git switch -c feature/smart-workspace` then `git add -A` (respecting excludes) and commit "Checkpoint: owner customizations before Smart Workspace"
  4. Baseline test run inside Docker, saved to WORKSPACE_TEST_REPORT.md
