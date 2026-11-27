---
name: horilla-attendance
description: Change anything that touches attendance, sign-in/sign-out, breaks, time corrections, work records, overtime or payslips in the bevy-horilla HR app. Use whenever a task mentions clock in or out, the Workspace card, Fix My Times, attendance validation, worked hours, overtime approval, work records, late/early rules, shifts and night shifts, daily updates, reminders, or payroll calculation. Covers the single-source-of-truth rule, how validation gates payroll, the safe correction sequence, idempotency, and what must be tested before merging.
---

# Attendance and payroll changes

This is the highest-consequence area of the app. Attendance rows feed payslips, so a change here can
pay someone the wrong amount, and there is no CI on `staging` to catch it.

Read before planning: `docs/compliance/workspace-attendance-integrity.md`.
Current behaviour and every setting: `docs/reference/WORKSPACE.md`.
Design record, including the numbered decisions D1–D5: `WORKSPACE_IMPLEMENTATION_PLAN.md` (history,
not live).

## The mechanism, in order

Know this before changing anything.

1. **Sign in** — `attendance/views/clock_in_out.py`: `clock_in()` (web) and `ClockInAPIView` (API)
   resolve the shift and the attendance date (night shifts use a noon-to-noon window), then call
   `clock_in_attendance_and_activity()`, which creates or reuses the day's `Attendance` and opens an
   `AttendanceActivity`. IP restriction (`AttendanceAllowedIP`) and geofencing are enforced when
   enabled.
2. **Sign out** — `clock_out_attendance_and_activity()` closes the activity, sums durations into
   `attendance_worked_hour`, runs `overtime_calculation()`, then sets
   `attendance_validated = attendance_validate(attendance)`.
3. **Auto-validation** — `attendance/views/views.py::attendance_validate`: validated only if worked
   time is at most `AttendanceValidationCondition.validation_at_work` (default 09:00) and at least
   the optional minimum. **Longer days stay unvalidated until HR validates them.**
4. **Payroll reads only validated attendance** — `payroll/methods/payslip_calc.py` and
   `payroll/methods/methods.py::get_attendance()` filter `attendance_validated=True`.
   `payroll/methods/payroll_run.py` lists unvalidated days and unapproved overtime as HR work.
5. **Overtime pay additionally requires `attendance_overtime_approve=True`** — an HR decision,
   separate from validation.
6. **Work records** — `attendance/signals.py::update_work_record_from_attendance` sets `WorkRecords`
   to `CONF` ("Validate the attendance") when unvalidated, else FDP / HDP / ABS. Payroll and reports
   read work records.
7. **Breaks** — starting a break closes the running activity, ending it opens a new one, so break
   time is excluded from worked time (`attendance/views/break_in_out.py`).
8. **History** — `Attendance` and `AttendanceActivity` already use `HorillaAuditLog`
   (`simple_history`).

## The rules

**Workspace never stores attendance times.** Go through
`clock_in_attendance_and_activity()` / `clock_out_attendance_and_activity()`. Workspace tables hold
metadata only: `WorkspaceAttendanceEvent`, `WorkspaceAttendanceMeta`, `AttendanceCorrectionLog`,
`WorkspaceIdempotencyKey`.

**Validation is touched narrowly or not at all.** A Workspace sign-out or self-correction sets
`attendance_validated=True` on **that one row** and records it in `WorkspaceAttendanceMeta`. The
global `attendance_validate()` rule and HR's validation pages stay as they are. The policy is one
switch, `WORKSPACE_AUTO_VALIDATE`.

**Overtime approval is never automated.** Base pay counts immediately; overtime pay still needs HR.

**Events are append-only.** `WorkspaceAttendanceEvent` uses `AppendOnlyQuerySet` — do not add an
update or delete path. Every action writes one, with `reported_time` (what the employee says) and
`recorded_at` (the server clock) as separate facts.

**Every mutating API call is idempotent.** An `Idempotency-Key` header is required and a repeat
replays the stored response, keyed by `(employee, key)`. A retrying desktop client must not
double-clock anyone.

**Concurrency is handled with a lock.** `transaction.atomic()` plus `select_for_update()` on the
employee row. An impossible transition is a friendly no-op, not an error page.

## The safe correction sequence

**The reference implementation is `HorillaAdapter.correct_times()` in
`workspace_attendance/adapters/horilla.py`**, reached from `correct_times()` in
`workspace_attendance/services.py`. Read it before writing a correction path.

Do **not** copy `attendance/views/requests.py::approve_validate_attendance_request()`. It is HR's
approval path, not a correction reference: its `AttendanceActivity` sync is gated on
`attendance_clock_out is None or attendance_clock_out_date is None`, so for a **completed** day it
skips the activity sync entirely, it only ever touches the activity's `clock_in` side, and it does
not recompute worked hours from the activity sum. Copying it leaves activity rows out of step with
the corrected clock times.

What the adapter actually does, in order:

1. **Refuse early.** A day with a pending attendance request (`is_validate_request`) is refused —
   cancel the request first. So is a day with an open break.
2. **Resolve the shift** the day was recorded under (a brand-new day uses the employee's current
   shift), and derive the night-shift window from it. Night shifts place an overnight sign-out on the
   next calendar date while `work_date` stays the shift date.
3. **Edit the ends, not the middle.** The **first** activity's `clock_in` and the **last**
   activity's `clock_out` are updated; the break segments between them are untouched. A missing day
   creates the `Attendance` plus one activity; an `Attendance` with no activities (an import) gets
   one rebuilt from the row.
4. **Re-read the activities in order**, then set `attendance_clock_in` from the first and
   `attendance_clock_out` from the last — or `None` when the last activity is still open.
5. **Sum worked hours across every closed activity** and store it with `format_time()`. This is the
   step the HR approval path does not have.
6. **Recompute `overtime_calculation()` — and refuse the whole correction** if HR has already
   approved overtime for that day and the new amount would differ (`code="overtime_approved"`, the
   transaction rolls back). A self-correction must never change an approved amount payroll will pay.
7. **Recompute late / early flags without destroying penalties**: delete only the
   `AttendanceLateComeEarlyOut` rows that have no `penaltyaccounts_set`, then re-run `late_come()`
   and `early_out()`. A flag that already carries a penalty survives.
8. Save, so the signals update `WorkRecords`.

Validation is applied by the **service**, not the adapter: `services.correct_times()` calls
`adapter.mark_valid_for_payroll()` only when `WORKSPACE_AUTO_VALIDATE` is on **and**
`attendance_clock_out is not None`. An open day is never marked valid.

Other constraints on Fix My Times: within `WORKSPACE_CORRECTION_WINDOW_DAYS` (30) calendar days and
not in the future — both checked for new corrections only, so a retry after midnight still replays a
correction saved before midnight. Sign-out must be after sign-in, and a new sign-in must fall before
the first break or sign-out ("Sign in must be before your first break or sign out"). It does not
create or touch a Horilla attendance request.

## Time zones

`TIME_ZONE` defaults to `Asia/Kolkata` when the environment does not set it, and `USE_TZ = True`.
Night shifts use a noon-to-noon attendance-date window. Most "the time is wrong" bugs here are one
of these two, not the logic.

## Before merging

- [ ] A payslip built from a day your change touched counts it exactly as an HR-validated day would.
      This is the test that matters; write it.
- [ ] Already-validated rows are unaffected, and you have said in the PR what happens to payslips
      already generated.
- [ ] Overtime approval is unchanged.
- [ ] `WorkRecords` end up in the right state (the signal ran).
- [ ] Repeating the same API call with the same idempotency key writes nothing new.
- [ ] Two simultaneous actions serialise rather than double-writing.
- [ ] A night shift and a half day both behave.
- [ ] Click-tested on the Workspace card, the HR attendance list, and the employee's own view.
- [ ] `/hr-check` passes, including `makemigrations --check --dry-run`.

If the change needs `payroll/methods/`, stop and say so — it is a protected path
(`docs/compliance/protected-paths.md`) and needs its own PR and an explicit decision.
