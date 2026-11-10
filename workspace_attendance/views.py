"""
Web views of the My Workspace card and Fix My Times.

Every attendance action goes through workspace_attendance.services; this file
never touches attendance models directly.
"""

import logging
from datetime import datetime
from functools import wraps

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from attendance.methods.utils import get_client_ip
from horilla.decorators import login_required as horilla_login_required
from workspace_attendance import conf, services
from workspace_attendance.adapters import get_adapter

logger = logging.getLogger(__name__)


def login_required(view_func):
    """
    Horilla's login_required (redirects visitors to the login page), except that
    a signed-in user without an employee profile reaches the view, which then
    answers with an empty card instead of a redirect or a page refresh loop.
    """
    horilla_wrapped = horilla_login_required(view_func)

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and user.is_active and get_adapter().get_employee(user) is None:
            return view_func(request, *args, **kwargs)
        return horilla_wrapped(request, *args, **kwargs)

    return wrapped


def _employee(request):
    return get_adapter().get_employee(request.user)


def _coords(request):
    try:
        latitude = float(request.POST.get("latitude", ""))
        longitude = float(request.POST.get("longitude", ""))
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return {"latitude": latitude, "longitude": longitude}


# --------------------------------------------------------------------------- card
def _render_card(request, employee, message="", error="", error_code=""):
    context = {
        "state": services.get_state(employee),
        "break_reasons": get_adapter().break_reasons(),
        "window_days": conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS"),
        "message": message,
        "error": error,
        "error_code": error_code,
    }
    return render(request, "workspace_attendance/workspace_card.html", context)


@login_required
@require_http_methods(["GET", "HEAD"])
def workspace_card(request):
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")
    return _render_card(request, employee)


def _run_action(request, call):
    """Run one service call and re-render the card with its message or error."""
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")
    message = error = error_code = ""
    try:
        _status, body = call(employee)
        message = body.get("message", "")
    except services.WorkspaceError as exc:
        error, error_code = exc.message, exc.code
    except Exception:
        logger.exception("Workspace action failed")
        error = _("Something went wrong. Please try again.")
    return _render_card(request, employee, message=message, error=error, error_code=error_code)


@login_required
@require_POST
def sign_in(request):
    ip, coords = get_client_ip(request), _coords(request)
    return _run_action(
        request, lambda e: services.sign_in(e, source="web", client_ip=ip, coords=coords)
    )


@login_required
@require_POST
def sign_out(request):
    ip, coords = get_client_ip(request), _coords(request)
    return _run_action(
        request, lambda e: services.sign_out(e, source="web", client_ip=ip, coords=coords)
    )


@login_required
@require_POST
def break_start(request):
    reason = request.POST.get("reason", "")
    note = request.POST.get("note", "")
    return _run_action(request, lambda e: services.start_break(e, reason, note, source="web"))


@login_required
@require_POST
def break_end(request):
    return _run_action(request, lambda e: services.end_break(e, source="web"))


@login_required
@require_POST
def away(request):
    is_away = request.POST.get("away") == "1"
    return _run_action(request, lambda e: services.set_away(e, is_away, source="web"))


# ------------------------------------------------------------------- fix my times
def _parse_time(raw, label):
    """'' -> None, 'HH:MM' (or HH:MM:SS) -> time. Raises ValueError with a friendly message."""
    raw = (raw or "").strip()
    if not raw:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).time().replace(second=0, microsecond=0)
        except ValueError:
            continue
    raise ValueError(_("%(label)s is not a valid time. Use the format HH:MM, for example 09:30.") % {"label": label})


def _row(day, sign_in_value=None, sign_out_value=None, message="", error=""):
    def fmt(value):
        return value.strftime("%H:%M") if value else ""

    return {
        **day,
        "sign_in_value": fmt(day["sign_in"]) if sign_in_value is None else sign_in_value,
        "sign_out_value": fmt(day["sign_out"]) if sign_out_value is None else sign_out_value,
        "message": message,
        "error": error,
    }


@login_required
@require_http_methods(["GET", "HEAD"])
def fix_times(request):
    employee = _employee(request)
    days = []
    if employee is not None:
        days = [_row(day) for day in services.recent_days(employee)]
    context = {
        "rows": days,
        "window_days": conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS"),
        "has_employee": employee is not None,
    }
    return render(request, "workspace_attendance/fix_times.html", context)


@login_required
@require_POST
def fix_times_save(request):
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")

    raw_date = request.POST.get("date", "")
    raw_in = request.POST.get("sign_in", "")
    raw_out = request.POST.get("sign_out", "")
    try:
        work_date = datetime.strptime(raw_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        return render(
            request,
            "workspace_attendance/fix_times_row.html",
            {"row": {"date": None, "sign_in_value": raw_in, "sign_out_value": raw_out,
                     "error": _("That date is not valid. Please reload the page and try again.")}},
        )

    base = {"date": work_date, "sign_in": None, "sign_out": None, "worked": None, "missing_sign_out": False}
    try:
        sign_in_time = _parse_time(raw_in, _("Sign in time"))
        sign_out_time = _parse_time(raw_out, _("Sign out time"))
    except ValueError as exc:
        return render(
            request,
            "workspace_attendance/fix_times_row.html",
            {"row": _row(base, raw_in, raw_out, error=str(exc))},
        )

    try:
        _status, body = services.correct_times(
            employee, work_date, sign_in_time, sign_out_time, actor=request.user, source="web"
        )
    except services.WorkspaceError as exc:
        return render(
            request,
            "workspace_attendance/fix_times_row.html",
            {"row": _row(base, raw_in, raw_out, error=exc.message)},
        )
    except Exception:
        logger.exception("Fix My Times failed")
        return render(
            request,
            "workspace_attendance/fix_times_row.html",
            {"row": _row(base, raw_in, raw_out, error=_("Something went wrong. Please try again."))},
        )

    fresh = next((d for d in services.recent_days(employee) if d["date"] == work_date), base)
    return render(
        request,
        "workspace_attendance/fix_times_row.html",
        {"row": _row(fresh, message=body.get("message", ""))},
    )
