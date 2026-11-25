# Workspace attendance integrity

Attendance feeds payroll. The Smart Employee Workspace (`workspace_attendance`, `daily_updates`,
`workspace_reminders`) lets employees sign in and out and correct their own times with no approval
step, which only stays safe because of a narrow set of invariants.

Design and settings: [`reference/WORKSPACE.md`](../reference/WORKSPACE.md). The decision record it
implements is `WORKSPACE_IMPLEMENTATION_PLAN.md` (sections 3 and 5).

## Do

- Go through Horilla's own functions for every time change:
  `clock_in_attendance_and_activity()` / `clock_out_attendance_and_activity()`, and the correction
  sequence that `attendance/views/requests.py::approve_validate_attendance_request()` demonstrates
  (update fields, sync the matching `AttendanceActivity`, set validated, re-run `late_come()` and
  `early_out()`).
- Keep Workspace tables to metadata only: `WorkspaceAttendanceEvent`,
  `WorkspaceAttendanceMeta`, `AttendanceCorrectionLog`, `WorkspaceIdempotencyKey`.
- Write a `WorkspaceAttendanceEvent` for every sign in, sign out, break start/end and correction,
  with both timestamps: `reported_time` (what the employee says) and `recorded_at` (the server
  clock).
- Run every attendance action inside `transaction.atomic()` with `select_for_update()` on the
  employee row, so two clicks serialise.
- Refuse an impossible transition as a friendly no-op — "sign out while not signed in" is not an
  error page.
- Require an `Idempotency-Key` header on every mutating Workspace API call, and replay the stored
  response for a repeated key.
- Keep the auto-validation policy behind `WORKSPACE_AUTO_VALIDATE`, and keep overtime approval
  (`attendance_overtime_approve`) an HR decision.
- Respect the correction window (`WORKSPACE_CORRECTION_WINDOW_DAYS`): no future times, sign-out after
  sign-in, and reject a correction that would cut through an existing break with a message that says
  so.
- When you change what a Workspace record does to an `Attendance` row, test that a payslip built
  from it counts the same as an HR-validated day.

## Do not

- Store an attendance time in a Workspace table, or compute worked hours independently of Horilla's
  activity sums.
- Set `attendance_validated` on anything other than the single row the Workspace action touched, or
  change the global `attendance_validate()` rule or HR's validation pages to suit Workspace.
- Approve overtime from Workspace.
- Make `WorkspaceAttendanceEvent` mutable. It is append-only (`AppendOnlyQuerySet` in
  `workspace_attendance/models.py`) — do not add an update or delete path.
- Create or touch a Horilla attendance *request* from a Workspace correction. Fix My Times is not a
  request flow.
- Accept a mutating API call without an idempotency key, or key it by anything other than
  (employee, key).
- Let a reminder job write attendance. Reminders deliver and snooze; they do not change records.
