"""
breakfilters.py

Template filters used by the check in/check out component to show the break state
"""

from django import template

register = template.Library()


@register.filter(name="open_break")
def open_break(user):
    """
    Returns the running (not ended) break of the user, or None
    args:
        user    : request.user
    """
    from attendance.models import AttendanceBreak

    try:
        employee = user.employee_get
    except Exception:
        return None
    if employee is None:
        return None
    try:
        return (
            AttendanceBreak.objects.filter(
                employee_id=employee, end_datetime__isnull=True
            )
            .order_by("-id")
            .first()
        )
    except Exception:
        # e.g. the break table does not exist yet because the migration has not
        # been applied. Show the normal check in/out button instead of failing
        # every page that renders the navbar.
        return None


@register.filter(name="break_elapsed_seconds")
def break_elapsed_seconds(attendance_break):
    """
    Seconds passed since the break started
    """
    if attendance_break is None:
        return 0
    return attendance_break.duration_seconds()


@register.filter(name="is_away")
def is_away(user):
    """
    True when the user is on a break, or manually set Away and is still on the
    same check in session (a later check in or break end clears it).
    """
    if open_break(user):
        return True
    from attendance.models import AttendanceActivity, EmployeePresence

    try:
        employee = user.employee_get
        presence = EmployeePresence.objects.filter(employee_id=employee).first()
        if presence is None or presence.away_since is None:
            return False
        activity = (
            AttendanceActivity.objects.filter(
                employee_id=employee, clock_out__isnull=True
            )
            .order_by("id")
            .last()
        )
        if activity is None:
            return False
        if activity.in_datetime and activity.in_datetime > presence.away_since:
            return False
        return True
    except Exception:
        return False
