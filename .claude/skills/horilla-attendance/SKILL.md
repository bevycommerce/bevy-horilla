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

`attendance/views/requests.py::approve_validate_attendance_request()` is the reference
implementation. Copy its order:

1. Update `attendance_clock_in` / `attendance_clock_out` and their dates.
2. Sync the matching `AttendanceActivity` — the first activity's start, the last activity's end.
   Break segments in between are **preserved**.
3. Recompute worked hours from the activity sum.
4. Run `overtime_calculation()`, then `late_come()` and `early_out()`.
5. Set validation per the policy above.
6. Save, so the signals update `WorkRecords`.

Constraints on Fix My Times: within `WORKSPACE_CORRECTION_WINDOW_DAYS` (30) calendar days, no future
times, sign-out after sign-in (night shifts follow Horilla's own date rules), and a correction that
would cut through an existing break is **rejected with a message that says so**. It does not create
or touch a Horilla attendance request.

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
