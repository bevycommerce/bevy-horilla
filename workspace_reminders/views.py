"""
Portal popups (one large box on any portal page).

Midday (owner rule 2026-11-11): 4 hours after the employee signed in, then every
hour, until Midday is sent or skipped, or the employee signs out. Closing it
only hides it until the next hourly reminder. The reminder engine decides when
it is due (one ReminderDelivery per hour); this view only shows it.

Start your day (HR rule 2026-11-25): "Start your day now?" on the first portal
visit of a work day; closed, it comes back once after 30 minutes.

Last update before sign out (HR rule 2026-11-25): a sign out without the day's
last update opens a box to write it; sending it signs the employee out.
"""

from datetime import datetime

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_http_methods, require_POST

from attendance.methods.utils import get_client_ip
from daily_updates import services as updates
from daily_updates.models import COMBINED, MIDDAY, MiddaySkip
from workspace_attendance import services as attendance
from workspace_attendance.adapters import get_adapter
from workspace_attendance.views import SIGN_OUT_POPUP_FLAG, _coords, login_required
from workspace_reminders import conf, engine
from workspace_reminders.models import ReminderDelivery

TEMPLATE = "workspace_reminders/midday_popup.html"
START_TEMPLATE = "workspace_reminders/start_day_popup.html"
SIGN_OUT_TEMPLATE = "workspace_reminders/sign_out_popup.html"
WORKING = ("working", "away", "on_break")


def _employee(request):
    return get_adapter().get_employee(request.user)


def _open_midday(employee):
    for delivery in engine.open_reminders(employee):
        if delivery.kind == "midday":
            return delivery
    return None


def _own_delivery(employee, delivery_id):
    return ReminderDelivery.objects.filter(pk=delivery_id, employee=employee, kind="midday").first()


@login_required
@require_http_methods(["GET", "HEAD"])
def popup(request):
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")
    if request.session.pop(SIGN_OUT_POPUP_FLAG, False):
        box = _sign_out_box(request, employee)
        if box is not None:
            return box
    delivery = _open_midday(employee)
    if delivery is not None:
        return render(request, TEMPLATE, _ctx(delivery, text=""))
    start = engine.start_day_box(employee)
    if start is not None:
        return render(request, START_TEMPLATE, _start_ctx(start))
    return HttpResponse("")


@login_required
@require_POST
def close(request, delivery_id):
    employee = _employee(request)
    if employee:
        engine.acknowledge(employee, delivery_id)
    return HttpResponse("")


def _comeback():
    """How long until a closed box comes back, in words ("1 hour" normally, "1 minute" in test mode)."""
    minutes = conf.midday_repeat_minutes()
    if minutes % 60 == 0:
        hours = minutes // 60
        return ngettext("%(n)d hour", "%(n)d hours", hours) % {"n": hours}
    return ngettext("%(n)d minute", "%(n)d minutes", minutes) % {"n": minutes}


def _ctx(delivery, **extra):
    return {"comeback": _comeback(), "delivery": delivery,
            "combine": engine.combine_mode(delivery.employee, delivery.work_date), **extra}


def _done(request, message):
    return render(request, TEMPLATE, {"done": True, "message": message})


@login_required
@require_POST
def submit_midday(request, delivery_id):
    employee = _employee(request)
    delivery = _own_delivery(employee, delivery_id) if employee else None
    if delivery is None:
        return HttpResponse("")
    text = request.POST.get("summary", "")
    combine = engine.combine_mode(employee, delivery.work_date)
    try:
        updates.submit_update(employee, delivery.work_date, COMBINED if combine else MIDDAY, {"summary": text}, "web")
    except attendance.WorkspaceError as error:
        return render(request, TEMPLATE, _ctx(delivery, text=text, error=error.message))
    engine.acknowledge(employee, delivery.pk)
    if combine:
        return _done(request, _("Midday + End of Day update sent. Thank you."))
    return _done(request, _("Midday update sent. Thank you."))


@login_required
@require_POST
def skip_combine(request, delivery_id):
    employee = _employee(request)
    delivery = _own_delivery(employee, delivery_id) if employee else None
    if delivery is None:
        return HttpResponse("")
    try:
        updates.skip_midday(employee, delivery.work_date, MiddaySkip.COMBINE, "web")
    except attendance.WorkspaceError as error:
        return render(request, TEMPLATE, _ctx(delivery, error=error.message))
    engine.acknowledge(employee, delivery.pk)
    return _done(request, _("Midday skipped. At the end of the day, write one note for the whole day."))


@login_required
@require_POST
def sign_out(request, delivery_id):
    employee = _employee(request)
    delivery = _own_delivery(employee, delivery_id) if employee else None
    if delivery is None:
        return HttpResponse("")
    try:
        _status, body = attendance.sign_out(employee, "web")
    except attendance.WorkspaceError as error:
        if error.code == "update_required":
            engine.acknowledge(employee, delivery.pk)
            return _sign_out_box(request, employee) or HttpResponse("")
        return render(request, TEMPLATE, _ctx(delivery, error=error.message))
    engine.acknowledge(employee, delivery.pk)
    return _card_refresh(
        _done(request, body.get("message") or _("Signed out at %(time)s.") % {"time": timezone.localtime().strftime("%H:%M")})
    )


def _card_refresh(response):
    """Ask the My Workspace card to reload, so it shows the new state at once."""
    response["HX-Trigger"] = "wsCardRefresh"
    return response


# ------------------------------------------------------------- start your day
def _start_comeback():
    minutes = conf.get()["start_day_repeat_minutes"]
    return ngettext("%(n)d minute", "%(n)d minutes", minutes) % {"n": minutes}


def _start_ctx(delivery, **extra):
    return {"delivery": delivery, "comeback": _start_comeback(), **extra}


def _own_start(employee, delivery_id):
    return ReminderDelivery.objects.filter(pk=delivery_id, employee=employee, kind=engine.START_DAY).first()


@login_required
@require_POST
def start_day(request, delivery_id):
    employee = _employee(request)
    delivery = _own_start(employee, delivery_id) if employee else None
    if delivery is None:
        return HttpResponse("")
    try:
        _status, body = attendance.sign_in(
            employee, "web", client_ip=get_client_ip(request), coords=_coords(request)
        )
    except attendance.WorkspaceError as error:
        return render(request, START_TEMPLATE, _start_ctx(delivery, error=error.message, error_code=error.code))
    engine.acknowledge(employee, delivery.pk)
    return _card_refresh(render(request, START_TEMPLATE, {"done": True, "message": body.get("message", "")}))


@login_required
@require_POST
def start_day_close(request, delivery_id):
    employee = _employee(request)
    if employee and _own_start(employee, delivery_id):
        engine.acknowledge(employee, delivery_id)
    return HttpResponse("")


# ------------------------------------------------- last update before sign out
def _sign_out_box(request, employee, **extra):
    """The "send your last update" box, or None when the employee may sign out already."""
    state = attendance.get_state(employee)
    if state["status"] not in WORKING:
        return None
    work_date = state["work_date"]
    needed = attendance.required_update(employee, work_date)
    if needed is None:
        return None
    context = {"work_date": work_date, "combined": needed == COMBINED, "text": "", **extra}
    return render(request, SIGN_OUT_TEMPLATE, context)


@login_required
@require_POST
def sign_out_with_update(request):
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")
    state = attendance.get_state(employee)
    if state["status"] not in WORKING:
        return _card_refresh(_done(request, _("You are not signed in right now.")))
    work_date = state["work_date"]
    text = request.POST.get("summary", "")
    try:
        posted = datetime.strptime(request.POST.get("work_date", ""), "%Y-%m-%d").date()
    except ValueError:
        posted = None
    if posted != work_date:
        # the box was opened for another day (for example before midnight)
        return _sign_out_box(request, employee, text=text) or HttpResponse("")
    needed = attendance.required_update(employee, work_date)
    if needed is not None:
        try:
            updates.submit_update(employee, work_date, needed, {"summary": text}, "web")
        except attendance.WorkspaceError as error:
            if attendance.required_update(employee, work_date) is not None:
                return _sign_out_box(request, employee, text=text, error=error.message, error_code=error.code)
    try:
        _status, body = attendance.sign_out(
            employee, "web", client_ip=get_client_ip(request), coords=_coords(request)
        )
    except attendance.WorkspaceError as error:
        box = _sign_out_box(request, employee, text=text, error=error.message, error_code=error.code)
        if box is not None:
            return box
        # the update is saved; only the sign out failed (for example the location check)
        response = render(
            request, SIGN_OUT_TEMPLATE, {"done": True, "message": _("Update sent.") + " " + error.message}
        )
        return _card_refresh(response)
    return _card_refresh(_done_sign_out(request, body))


def _done_sign_out(request, body):
    message = _("Update sent.") + " " + (body.get("message") or "")
    return render(request, SIGN_OUT_TEMPLATE, {"done": True, "message": message.strip()})
