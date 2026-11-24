"""
Break and Away logic without any HTTP request.

Moved out of attendance/views/break_in_out.py so the web views, the Smart
Workspace card and the desktop companion API all run exactly the same rules:

- Starting a break closes the running AttendanceActivity.
- Ending a break opens a new AttendanceActivity.
- So break time is never counted as worked time.
- "Away" only stores a timestamp; it changes nothing else.
"""

from datetime import date

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from attendance.models import AttendanceActivity, AttendanceBreak, EmployeePresence


class BreakError(Exception):
    """A break action that cannot be done; the message is safe to show the employee."""


def open_break(employee):
    """The running break of the employee, or None."""
    return (
        AttendanceBreak.objects.filter(employee_id=employee, end_datetime__isnull=True)
        .order_by("-id")
        .first()
    )


def open_activity(employee):
    """The running (not clocked out) attendance activity of the employee, or None."""
    return (
        AttendanceActivity.objects.filter(employee_id=employee, clock_out__isnull=True)
        .order_by("attendance_date", "id")
        .last()
    )


def start_break(employee, reason, note="", now=None):
    """
    Start a break.

    Returns (break, created). created is False when a break was already running
    (nothing changes in that case). Raises BreakError for an invalid reason or
    when the employee is not checked in.
    """
    if reason not in dict(AttendanceBreak.REASON_CHOICES):
        raise BreakError(_("Please choose a valid break reason."))
    note = (note or "").strip()[:300]

    running = open_break(employee)
    if running is not None:
        return running, False

    activity = open_activity(employee)
    if activity is None:
        raise BreakError(_("You need to be checked in to start a break."))

    now = now or timezone.localtime()
    activity.clock_out = now.time().replace(microsecond=0)
    activity.clock_out_date = date.today()
    activity.out_datetime = now
    activity.save()

    new_break = AttendanceBreak.objects.create(
        employee_id=employee,
        attendance_date=activity.attendance_date,
        reason=reason,
        note=note,
        start_datetime=now,
    )
    return new_break, True


def end_break(employee, now=None):
    """
    End the running break and open a new attendance activity.

    Returns the ended break, or None when no break was running.
    """
    running = open_break(employee)
    if running is None:
        return None

    last_activity = (
        AttendanceActivity.objects.filter(
            employee_id=employee, attendance_date=running.attendance_date
        )
        .order_by("id")
        .last()
    )
    now = now or timezone.localtime()
    running.end_datetime = now
    running.save()

    AttendanceActivity.objects.create(
        employee_id=employee,
        attendance_date=running.attendance_date,
        clock_in_date=date.today(),
        shift_day=last_activity.shift_day if last_activity else None,
        clock_in=now.time().replace(microsecond=0),
        in_datetime=now,
    )
    return running


def set_away(employee, now=None):
    """
    Mark the employee Away. Only allowed while checked in or on a break.
    Raises BreakError otherwise.
    """
    if open_activity(employee) is None and open_break(employee) is None:
        raise BreakError(_("You need to be checked in to set Away."))
    presence, _created = EmployeePresence.objects.get_or_create(employee_id=employee)
    presence.away_since = now or timezone.now()
    presence.save()
    return presence


def clear_away(employee):
    """Remove the Away mark (no other change)."""
    presence, _created = EmployeePresence.objects.get_or_create(employee_id=employee)
    if presence.away_since is not None:
        presence.away_since = None
        presence.save()
    return presence
