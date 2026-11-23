"""
break_log.py

Break Log page: every break with its reason, note, start, end and length,
plus a CSV download. Users with the view attendance permission see every
employee, everyone else sees only their own breaks.
"""

import csv
from datetime import date

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from attendance.methods.utils import employee_exists
from attendance.models import AttendanceBreak
from employee.models import Employee
from horilla.decorators import login_required


def _format_seconds(seconds):
    """
    Seconds as HH:MM:SS
    """
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"


def _csv_cell(value):
    """
    Text for one CSV cell. A cell starting with = + - @ is prefixed with ' so a
    spreadsheet never runs it as a formula.
    """
    text = "" if value is None else str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        text = "'" + text
    return text


def _break_log_csv(rows, date_from, date_to, export_all=False):
    """
    The break log rows as a CSV download (opens in Excel and Google Sheets).
    """
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    name = (
        "break-log_all"
        if export_all
        else (f"break-log_{date_from.isoformat()}_to_{date_to.isoformat()}")
    )
    response["Content-Disposition"] = f'attachment; filename="{name}.csv"'

    response.write("\ufeff")  # lets Excel read the file as UTF-8
    writer = csv.writer(response)
    writer.writerow(
        [
            "Employee",
            "Date",
            "Reason",
            "Note",
            "Start",
            "End",
            "Duration (HH:MM:SS)",
            "Status",
        ]
    )
    for row in rows:
        start = timezone.localtime(row["start"]) if row["start"] else None
        end = timezone.localtime(row["end"]) if row["end"] else None
        writer.writerow(
            [
                _csv_cell(row["employee"]),
                row["attendance_date"].isoformat(),
                _csv_cell(row["reason"]),
                _csv_cell(row["note"]),
                start.strftime("%Y-%m-%d %H:%M:%S") if start else "",
                end.strftime("%Y-%m-%d %H:%M:%S") if end else "",
                row["duration"],
                "Running" if row["running"] else "Ended",
            ]
        )
    return response


@login_required
def break_log(request):
    """
    List of breaks. Users with the view attendance permission see every
    employee, everyone else sees only their own breaks.
    ?export=csv downloads the same rows (same dates, same people) as a CSV file;
    ?export=csv&all=1 downloads every break the user may see, all dates.
    """
    today = date.today()

    def read_date(name, default):
        try:
            return date.fromisoformat(request.GET.get(name, ""))
        except ValueError:
            return default

    date_from = read_date("from", today.replace(day=1))
    date_to = read_date("to", today)

    export_all = request.GET.get("export") == "csv" and request.GET.get("all") == "1"
    breaks = AttendanceBreak.objects.select_related("employee_id")
    if not export_all:
        breaks = breaks.filter(attendance_date__range=(date_from, date_to))

    can_view_all = request.user.is_superuser or request.user.has_perm(
        "attendance.view_attendance"
    )
    if not can_view_all:
        employee, work_info = employee_exists(request)
        breaks = breaks.filter(employee_id=employee) if employee else breaks.none()
    else:
        # only employees of the company chosen in the company switcher (the
        # Employee manager applies that selection, as other attendance views do)
        breaks = breaks.filter(employee_id__in=Employee.objects.values("pk"))

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

    if request.GET.get("export") == "csv":
        return _break_log_csv(rows, date_from, date_to, export_all)

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
