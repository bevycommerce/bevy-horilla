"""
break_in_out.py

Endpoints to start and end a break while an employee is checked in.
Starting a break closes the running attendance activity, ending it opens a new
one, so the time between them is not counted as worked time.
"""

import logging
from datetime import date

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from attendance.methods.utils import employee_exists
from attendance.models import AttendanceActivity, AttendanceBreak, EmployeePresence
from attendance.views.clock_in_out import clock_in, clock_out
from horilla.decorators import hx_request_required, login_required
from horilla.http.response import HorillaRedirect

logger = logging.getLogger(__name__)

COMPONENT = "attendance/components/in_out_component.html"


@login_required
@hx_request_required
def break_start(request):
    """
    Start a break. Needs ?reason=<one of AttendanceBreak.REASON_CHOICES keys>
    """
    employee, work_info = employee_exists(request)
    if not employee or work_info is None:
        messages.error(
            request,
            _("Break Unavailable: Your employee profile or work information is incomplete."),
        )
        return HorillaRedirect(request)

    reason = request.GET.get("reason")
    note = (request.GET.get("note") or "").strip()[:300]
    if reason not in dict(AttendanceBreak.REASON_CHOICES):
        messages.error(request, _("Please choose a valid break reason."))
        return HorillaRedirect(request)

    if AttendanceBreak.objects.filter(
        employee_id=employee, end_datetime__isnull=True
    ).exists():
        # a break is already running, just show the current state
        return render(request, COMPONENT, {})

    activity = (
        AttendanceActivity.objects.filter(employee_id=employee, clock_out__isnull=True)
        .order_by("attendance_date", "id")
        .last()
    )
    if activity is None:
        messages.error(request, _("You need to be checked in to start a break."))
        return HorillaRedirect(request)

    now = timezone.localtime()
    activity.clock_out = now.time().replace(microsecond=0)
    activity.clock_out_date = date.today()
    activity.out_datetime = now
    activity.save()

    AttendanceBreak.objects.create(
        employee_id=employee,
        attendance_date=activity.attendance_date,
        reason=reason,
        note=note,
        start_datetime=now,
    )
    return render(request, COMPONENT, {})


@login_required
@hx_request_required
def break_end(request):
    """
    End the running break and continue the work timer
    """
    employee, work_info = employee_exists(request)
    if not employee or work_info is None:
        messages.error(
            request,
            _("Break Unavailable: Your employee profile or work information is incomplete."),
        )
        return HorillaRedirect(request)

    running_break = (
        AttendanceBreak.objects.filter(employee_id=employee, end_datetime__isnull=True)
        .order_by("-id")
        .first()
    )
    if running_break is None:
        return render(request, COMPONENT, {})

    last_activity = (
        AttendanceActivity.objects.filter(
            employee_id=employee, attendance_date=running_break.attendance_date
        )
        .order_by("id")
        .last()
    )
    now = timezone.localtime()
    running_break.end_datetime = now
    running_break.save()

    AttendanceActivity.objects.create(
        employee_id=employee,
        attendance_date=running_break.attendance_date,
        clock_in_date=date.today(),
        shift_day=last_activity.shift_day if last_activity else None,
        clock_in=now.time().replace(microsecond=0),
        in_datetime=now,
    )
    return render(request, COMPONENT, {})


def _format_seconds(seconds):
    """
    Seconds as HH:MM:SS
    """
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


@login_required
def break_log(request):
    """
    List of breaks. Users with the view attendance permission see every
    employee, everyone else sees only their own breaks.
    """
    today = date.today()

    def read_date(name, default):
        try:
            return date.fromisoformat(request.GET.get(name, ""))
        except ValueError:
            return default

    date_from = read_date("from", today.replace(day=1))
    date_to = read_date("to", today)

    breaks = AttendanceBreak.objects.filter(
        attendance_date__range=(date_from, date_to)
    ).select_related("employee_id")

    can_view_all = request.user.is_superuser or request.user.has_perm(
        "attendance.view_attendance"
    )
    if not can_view_all:
        employee, work_info = employee_exists(request)
        breaks = breaks.filter(employee_id=employee) if employee else breaks.none()

    rows = []
    total_seconds = 0
    for item in breaks.order_by("-start_datetime"):
        seconds = item.duration_seconds()
        total_seconds += seconds
        employee_obj = item.employee_id
        get_name = getattr(employee_obj, "get_full_name", None)
        rows.append(
            {
                "employee": get_name() if callable(get_name) else str(employee_obj),
                "attendance_date": item.attendance_date,
                "reason": item.get_reason_display(),
                "note": item.note,
                "start": item.start_datetime,
                "end": item.end_datetime,
                "duration": _format_seconds(seconds),
                "running": item.end_datetime is None,
            }
        )

    return render(
        request,
        "attendance/break_log.html",
        {
            "rows": rows,
            "total_duration": _format_seconds(total_seconds),
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "can_view_all": can_view_all,
        },
    )


@login_required
@hx_request_required
def set_status(request):
    """
    Manual status from the profile menu: ?status=online|away|offline
    online  : ends a running break, or checks in when not checked in
    offline : ends a running break if any, then checks out when checked in
    away    : only marks the user away, nothing else changes
    """
    status = request.GET.get("status")
    employee, work_info = employee_exists(request)
    if status not in ("online", "away", "offline") or not employee or work_info is None:
        messages.error(request, _("Could not change the status."))
        return HorillaRedirect(request)

    open_activity = AttendanceActivity.objects.filter(
        employee_id=employee, clock_out__isnull=True
    ).exists()
    on_break = AttendanceBreak.objects.filter(
        employee_id=employee, end_datetime__isnull=True
    ).exists()
    presence, _created = EmployeePresence.objects.get_or_create(employee_id=employee)

    if status == "away":
        if open_activity or on_break:
            presence.away_since = timezone.now()
            presence.save()
        else:
            messages.error(request, _("You need to be checked in to set Away."))
    else:
        presence.away_since = None
        presence.save()
        if on_break:
            break_end(request)
            open_activity = True
        if status == "online" and not open_activity:
            clock_in(request)
        elif status == "offline" and open_activity:
            clock_out(request)

    response = HttpResponse()
    response["HX-Refresh"] = "true"
    return response
