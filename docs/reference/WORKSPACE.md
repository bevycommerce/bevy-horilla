# Smart Employee Workspace

Three Bevy apps — `workspace_attendance`, `daily_updates`, `workspace_reminders` — that give
employees a single card to sign in and out, take breaks, fix their own times, and send daily updates,
with reminders driving the rhythm. A desktop companion app ("BevyLoop", a separate repository)
drives the same API.

Rule: [`compliance/workspace-attendance-integrity.md`](../compliance/workspace-attendance-integrity.md).
API contract: [`../workspace_api.md`](../workspace_api.md).
Original design record: `WORKSPACE_IMPLEMENTATION_PLAN.md` at the repository root — the verified
baseline and the numbered decisions (D1–D5) this app implements. It is history, not a live doc; what
the code does now is here and in the code.

## The governing decision

**Workspace never stores attendance times.** Sign in and out always go through Horilla's own
`clock_in_attendance_and_activity()` / `clock_out_attendance_and_activity()`. Workspace tables hold
metadata only. Everything else below follows from that.

## Models

`workspace_attendance/models.py`:

| Model | Holds |
|---|---|
| `WorkspaceAttendanceMeta` | One-to-one with `Attendance`: `managed_by_workspace`, `last_source`, `last_corrected_at` |
| `WorkspaceAttendanceEvent` | One row per sign in, sign out, break start/end, correction — with `reported_time` (what the employee says) and `recorded_at` (server clock), plus `source` and `idempotency_key`. **Append-only** via `AppendOnlyQuerySet` |
| `AttendanceCorrectionLog` | What a Fix My Times correction changed |
| `WorkspaceIdempotencyKey` | `(employee, key)` unique, with the stored response replayed on a repeat |

`daily_updates/models.py`: `DailyUpdate`, `DailyUpdateRevision`, `MiddaySkip`.

`workspace_reminders/models.py`: `ReminderDelivery`, `ReminderSnooze`.

## Payroll compatibility

Horilla auto-validates an attendance day only when worked time is within
`AttendanceValidationCondition.validation_at_work` (default 09:00); longer days stay unvalidated
until HR validates them, and **payroll reads only validated attendance**
(`payroll/methods/payslip_calc.py`, `methods.get_attendance()`).

Workspace needs sign-outs and self-corrections to count immediately with no approval, so after a
Workspace sign-out or correction the service sets `attendance_validated=True` on **that single
`Attendance` row** and records it in `WorkspaceAttendanceMeta`. The global `attendance_validate()`
rule and HR's validation pages are untouched for every other record.

**Overtime stays an HR decision.** `attendance_overtime_approve` is not set by Workspace: base pay
counts immediately, overtime pay still needs approval, and the UI says so.

The whole policy is one switch, `WORKSPACE_AUTO_VALIDATE`, so it is not scattered through the code.

## Concurrency and idempotency

- Every attendance action runs in `transaction.atomic()` with `select_for_update()` on the
  employee's row, so two simultaneous clicks serialise.
- An impossible transition ("sign out while not signed in") is a friendly no-op, not an error.
- Every mutating API call requires an `Idempotency-Key` header. A repeated key replays the stored
  response. Keys are cleaned up by the 03:17 job
  ([`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md)); retention is `WORKSPACE_IDEMPOTENCY_DAYS`.

## Fix My Times

Employees correct their own times within `WORKSPACE_CORRECTION_WINDOW_DAYS` calendar days. No future
times; sign-out after sign-in (night shifts follow Horilla's own date rules). The window and
future checks run for **new** corrections only, so a retry after midnight still replays a correction
saved before midnight.

`services.correct_times()` wraps the policy; `HorillaAdapter.correct_times()`
(`workspace_attendance/adapters/horilla.py`) does the work and is the implementation to read:

- **Refused outright:** a day with a pending attendance request (cancel it first), or a day with an
  open break (end it first).
- **Existing record:** the **first** activity's `clock_in` and the **last** activity's `clock_out`
  are updated; break segments between them are untouched. A new sign-in must fall before the first
  break or sign-out, or it is rejected with that message.
- **Missing record:** create the `Attendance` plus one `AttendanceActivity` using the adapter's
  shift lookup. An `Attendance` with no activities (an import) gets one rebuilt from the row.
- **Then re-derive from the activities**, not from the input: clock in/out from the first and last,
  worked hours as the sum over every closed activity, then `overtime_calculation()`.
- **Refused if HR already approved overtime** for that day and the recomputed amount would differ
  (`code="overtime_approved"`) — the whole correction rolls back, so a self-correction can never
  change an approved amount payroll will pay.
- **Late / early flags** are recomputed, but a flag that already carries a penalty is kept: only
  `AttendanceLateComeEarlyOut` rows with no `penaltyaccounts_set` are deleted before re-running
  `late_come()` and `early_out()`.
- **Validation** is the service's call, not the adapter's: `mark_valid_for_payroll()` runs only when
  `WORKSPACE_AUTO_VALIDATE` is on **and** `attendance_clock_out is not None`. An open day is never
  marked valid.
- It does **not** create or touch a Horilla attendance request. Fix My Times is not a request flow.

Do not take `attendance/views/requests.py::approve_validate_attendance_request()` as the correction
reference. It is HR's approval path: its activity sync only runs when the clock-out is missing, it
touches the `clock_in` side only, and it does not recompute worked hours from the activities.

## Settings

`workspace_attendance/conf.py` holds the defaults; override any of them in Django settings. Read
them with `conf.get("NAME")`, never `getattr(settings, …)` directly.

| Setting | Default | Meaning |
|---|---|---|
| `WORKSPACE_ADAPTER` | `workspace_attendance.adapters.horilla.HorillaAdapter` | The seam between Workspace and the HR system |
| `WORKSPACE_CORRECTION_WINDOW_DAYS` | `30` | How far back an employee may fix their own times |
| `WORKSPACE_AUTO_VALIDATE` | `True` | Workspace-touched rows count for payroll immediately |
| `WORKSPACE_IDEMPOTENCY_DAYS` | `7` | How long a stored response is replayable |
| `WORKSPACE_SHOW_BREAK` | `False` | The "Take a Break" button on the card. Off by owner decision; a break started from the header still shows on the card with "End Break" |
| `WORKSPACE_HIDE_HEADER_CLOCK` | `True` | Hides Horilla's green check-in/out timer in the top bar |

`workspace_reminders/conf.py` is merged per key from `settings.WORKSPACE_REMINDERS`:

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `True` | Master switch |
| `stale_after_minutes` | `60` | A reminder is only sent within this long after becoming due, so the scheduler coming back online does not flood everyone |
| `snooze_choices` | `[15, 30]` | Snooze options offered |
| `kinds` | see below | Per-reminder anchor, offset, attempts, repeat |

Reminder kinds: `sign_in` (shift start), `sign_in_followup` (+30 min), `midday` (4 h **after sign-in**,
then hourly for up to 12 attempts until the update is sent or skipped or the employee signs out),
`eod` (30 min before shift end), `sign_out` (shift end).

`WORKSPACE_REMINDER_TEST_MINUTES=1` in the environment makes the Midday box arrive one minute after
sign-in and repeat every minute — a testing switch, capped at 120. Remove the line and restart to
return to the real cadence.

## Surfaces

| Surface | Where |
|---|---|
| The card and screens | `/workspace/` — `card/`, `sign-in/`, `sign-out/`, `break/start/`, `break/end/`, `away/`, `fix-times/`, `fix-times/save/` |
| Reminders UI | `/workspace/reminders/` |
| Daily Updates | `/daily-updates/` |
| Desktop / API | `/api/v1/workspace/v1/` — `updates/`, `reminders/`, and the attendance actions. Contract: [`../workspace_api.md`](../workspace_api.md) |

## Working on it

- Read the compliance rule before changing anything that writes an `Attendance` row.
- When you change what a Workspace action does to an attendance row, test that a payslip built from
  that day counts it exactly as an HR-validated day would.
- `workspace_attendance/adapters/` is the seam to Horilla. New HR-system coupling goes through the
  adapter, not inline in a view.
- Breaks: starting one closes the running `AttendanceActivity` and ending it opens a new one, so
  break time is excluded from worked time. The original implementation of this lives in
  `attendance/views/break_in_out.py`.
