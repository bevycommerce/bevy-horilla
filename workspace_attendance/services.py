"""
Smart Workspace attendance services.

Every entry point here is used by both the web card and the desktop API, so the
two can never behave differently. Rules implemented (see WORKSPACE_IMPLEMENTATION_PLAN.md):

D2  Workspace sign-outs and self-corrections count for payroll immediately
    (only the Attendance rows Workspace touches; HR overtime approval unchanged).
D3  Actions are serialized per employee (row lock) and duplicate-safe; an
    Idempotency-Key replays the first answer instead of acting twice.
D4  Every action stores the employee-reported time and the server time.
D5  Fix My Times within WORKSPACE_CORRECTION_WINDOW_DAYS, no approval.
D6  Corrections go to an append-only log.
"""

import re
from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from workspace_attendance import conf
from workspace_attendance.adapters import get_adapter
from workspace_attendance.adapters.base import AttendanceActionError
from workspace_attendance.models import (
    AttendanceCorrectionLog,
    WorkspaceAttendanceEvent,
    WorkspaceAttendanceMeta,
    WorkspaceIdempotencyKey,
)

IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_\-:.]{8,64}$")
SOURCES = {"web", "desktop", "api"}


class WorkspaceError(Exception):
    """A Workspace action that was refused. message is safe to show; status maps to HTTP."""

    def __init__(self, message, code="invalid", status=400):
        super().__init__(message)
        self.message = str(message)
        self.code = code
        self.status = status


# --------------------------------------------------------------------------- helpers
def _lock_employee(employee):
    """Serialize all Workspace actions of one employee (prevents double clicks racing)."""
    type(employee).objects.select_for_update().filter(pk=employee.pk).first()


def _check_source(source):
    if source not in SOURCES:
        raise WorkspaceError(_("Unknown source."), code="bad_source")


def _record_event(employee, action, work_date, reported_time, source, key="", attendance=None):
    return WorkspaceAttendanceEvent.objects.create(
        employee=employee,
        attendance=attendance,
        action=action,
        work_date=work_date,
        reported_time=reported_time,
        source=source,
        idempotency_key=key or "",
    )


def _touch_meta(attendance, source, corrected=False):
    if attendance is None:
        return
    meta, created = WorkspaceAttendanceMeta.objects.get_or_create(
        attendance=attendance, defaults={"last_source": source}
    )
    meta.last_source = source
    meta.managed_by_workspace = True
    if corrected:
        meta.last_corrected_at = timezone.now()
    meta.save()


def serialize_state(state):
    """Make an adapter state JSON-safe (ISO dates)."""

    def iso(value):
        return value.isoformat() if value is not None else None

    data = dict(state)
    data["work_date"] = iso(state.get("work_date"))
    for key in ("signed_in_at", "signed_out_at", "away_since"):
        data[key] = iso(state.get(key))
    if state.get("break"):
        brk = dict(state["break"])
        brk["started_at"] = iso(brk.get("started_at"))
        data["break"] = brk
    data["server_time"] = timezone.localtime().isoformat()
    return data


def run_idempotent(employee, key, action, func):
    """
    Run func() once per (employee, key). A repeated key returns the stored answer.
    func must return (status_code, response_dict) or raise WorkspaceError.
    Without a key the action simply runs (the web card relies on state checks).
    """
    if not key:
        return func()
    if not IDEMPOTENCY_KEY_RE.match(key):
        raise WorkspaceError(_("Invalid Idempotency-Key."), code="bad_idempotency_key")
    existing = WorkspaceIdempotencyKey.objects.filter(employee=employee, key=key).first()
    if existing is not None:
        if existing.action != action:
            raise WorkspaceError(
                _("This Idempotency-Key was already used for a different action."),
                code="idempotency_conflict",
                status=409,
            )
        response = dict(existing.response)
        response["replayed"] = True
        return existing.status_code, response
    try:
        with transaction.atomic():
            status, response = func()
            WorkspaceIdempotencyKey.objects.create(
                employee=employee, key=key, action=action, status_code=status, response=response
            )
    except IntegrityError:
        # a parallel request with the same key won the race; return its answer
        existing = WorkspaceIdempotencyKey.objects.get(employee=employee, key=key)
        response = dict(existing.response)
        response["replayed"] = True
        return existing.status_code, response
    return status, response


def cleanup_idempotency_keys():
    """Delete stored keys older than WORKSPACE_IDEMPOTENCY_DAYS (scheduled daily)."""
    limit = timezone.now() - timedelta(days=conf.get("WORKSPACE_IDEMPOTENCY_DAYS"))
    return WorkspaceIdempotencyKey.objects.filter(created_at__lt=limit).delete()[0]


# --------------------------------------------------------------------------- state
def get_state(employee):
    return get_adapter().get_state(employee)


# --------------------------------------------------------------------------- actions
def sign_in(employee, source, client_ip=None, coords=None, key=""):
    _check_source(source)
    adapter = get_adapter()

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            state = adapter.get_state(employee)
            if state["status"] in ("working", "away", "on_break"):
                return 200, {
                    "ok": True,
                    "changed": False,
                    "message": _("You are already signed in."),
                    "state": serialize_state(state),
                }
            try:
                adapter.check_allowed(employee, client_ip=client_ip, coords=coords)
            except AttendanceActionError as error:
                raise WorkspaceError(error.args[0], code=error.code, status=403) from error
            now = timezone.localtime()
            attendance = adapter.sign_in(employee, now)
            adapter.clear_away(employee)
            _record_event(employee, "sign_in", attendance.attendance_date, now, source, key, attendance)
            _touch_meta(attendance, source)
            state = adapter.get_state(employee)
            return 200, {
                "ok": True,
                "changed": True,
                "message": _("Signed in at %(time)s.") % {"time": now.strftime("%H:%M")},
                "state": serialize_state(state),
            }

    return run_idempotent(employee, key, "sign_in", do)


def sign_out(employee, source, client_ip=None, coords=None, key=""):
    _check_source(source)
    adapter = get_adapter()

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            state = adapter.get_state(employee)
            if state["status"] not in ("working", "away", "on_break"):
                return 200, {
                    "ok": True,
                    "changed": False,
                    "message": _("You are not signed in right now."),
                    "state": serialize_state(state),
                }
            try:
                adapter.check_allowed(employee, client_ip=client_ip, coords=coords)
            except AttendanceActionError as error:
                raise WorkspaceError(error.args[0], code=error.code, status=403) from error
            now = timezone.localtime()
            if state["status"] == "on_break":
                adapter.end_break(employee, now)
                _record_event(employee, "break_end", state["work_date"], now, source, key)
            attendance = adapter.sign_out(employee, now)
            if attendance is None:
                raise WorkspaceError(_("No open sign in was found to close."), code="nothing_open", status=409)
            adapter.clear_away(employee)
            if conf.get("WORKSPACE_AUTO_VALIDATE"):
                adapter.mark_valid_for_payroll(attendance)
            _record_event(employee, "sign_out", attendance.attendance_date, now, source, key, attendance)
            _touch_meta(attendance, source)
            state = adapter.get_state(employee)
            return 200, {
                "ok": True,
                "changed": True,
                "message": _("Signed out at %(time)s.") % {"time": now.strftime("%H:%M")},
                "state": serialize_state(state),
            }

    return run_idempotent(employee, key, "sign_out", do)


def start_break(employee, reason, note, source, key=""):
    _check_source(source)
    adapter = get_adapter()

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            now = timezone.localtime()
            try:
                brk, created = adapter.start_break(employee, reason, note, now)
            except AttendanceActionError as error:
                raise WorkspaceError(error.args[0], code=error.code, status=409) from error
            if created:
                _record_event(employee, "break_start", brk.attendance_date, now, source, key)
            return 200, {
                "ok": True,
                "changed": created,
                "message": _("Break started.") if created else _("You are already on a break."),
                "state": serialize_state(adapter.get_state(employee)),
            }

    return run_idempotent(employee, key, "break_start", do)


def end_break(employee, source, key=""):
    _check_source(source)
    adapter = get_adapter()

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            now = timezone.localtime()
            brk = adapter.end_break(employee, now)
            if brk is not None:
                _record_event(employee, "break_end", brk.attendance_date, now, source, key)
            return 200, {
                "ok": True,
                "changed": brk is not None,
                "message": _("Welcome back. Break ended.") if brk else _("You are not on a break."),
                "state": serialize_state(adapter.get_state(employee)),
            }

    return run_idempotent(employee, key, "break_end", do)


def set_away(employee, away, source, key=""):
    _check_source(source)
    adapter = get_adapter()

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            now = timezone.localtime()
            state = adapter.get_state(employee)
            if away:
                try:
                    adapter.set_away(employee, now)
                except AttendanceActionError as error:
                    raise WorkspaceError(error.args[0], code=error.code, status=409) from error
                _record_event(employee, "away", state["work_date"], now, source, key)
            else:
                adapter.clear_away(employee)
                _record_event(employee, "back", state["work_date"], now, source, key)
            return 200, {
                "ok": True,
                "changed": True,
                "message": _("Marked as away.") if away else _("Marked as back."),
                "state": serialize_state(adapter.get_state(employee)),
            }

    return run_idempotent(employee, key, "away" if away else "back", do)


def correct_times(employee, work_date, sign_in_time, sign_out_time, actor, source, key=""):
    """
    Fix My Times. sign_in_time / sign_out_time are datetime.time or None.
    Effective immediately; no approval. Every change is logged permanently.
    """
    _check_source(source)
    adapter = get_adapter()
    today = timezone.localdate()
    window = conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS")
    if work_date > today:
        raise WorkspaceError(_("You cannot fix times for a future day."), code="future")
    if work_date < today - timedelta(days=window):
        raise WorkspaceError(
            _("You can fix your own times for the last %(days)s days only. For older days, contact HR.")
            % {"days": window},
            code="outside_window",
        )
    if sign_in_time is None and sign_out_time is None:
        raise WorkspaceError(_("Enter a sign in or sign out time."), code="nothing_to_change")

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            now = timezone.localtime()
            try:
                attendance, changes = adapter.correct_times(employee, work_date, sign_in_time, sign_out_time, now)
            except AttendanceActionError as error:
                raise WorkspaceError(error.args[0], code=error.code) from error
            if conf.get("WORKSPACE_AUTO_VALIDATE") and attendance.attendance_clock_out is not None:
                adapter.mark_valid_for_payroll(attendance)
            for field, old, new in changes:
                AttendanceCorrectionLog.objects.create(
                    employee=employee,
                    attendance=attendance,
                    work_date=work_date,
                    field=field,
                    old_value=old,
                    new_value=new,
                    source=source,
                    actor=actor,
                    idempotency_key=key or "",
                )
            reported = sign_out_time or sign_in_time
            _record_event(
                employee,
                "correction",
                work_date,
                timezone.make_aware(datetime.combine(work_date, reported)),
                source,
                key,
                attendance,
            )
            _touch_meta(attendance, source, corrected=True)
            return 200, {
                "ok": True,
                "changed": bool(changes),
                "message": _("Times saved for %(day)s.") % {"day": work_date.strftime("%d %b %Y")}
                if changes
                else _("Nothing changed."),
                "changes": [{"field": f, "old": o, "new": n} for f, o, n in changes],
                "state": serialize_state(adapter.get_state(employee)),
            }

    return run_idempotent(employee, key, "correction", do)


def recent_days(employee, days=None):
    """Attendance of the last N days for the Fix My Times list (newest first)."""
    days = days or conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS")
    today = timezone.localdate()
    rows = get_adapter().attendance_by_day(employee, today - timedelta(days=days), today)
    result = []
    for offset in range(days + 1):
        day = today - timedelta(days=offset)
        row = rows.get(day) or {}
        result.append(
            {
                "date": day,
                "sign_in": row.get("sign_in"),
                "sign_out": row.get("sign_out"),
                "worked": row.get("worked"),
                "missing_sign_out": bool(row.get("sign_in") and not row.get("sign_out") and day < today),
            }
        )
    return result
