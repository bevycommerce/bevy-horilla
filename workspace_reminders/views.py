"""
Portal popup for the Midday reminder (owner rule 2026-11-11).

A large box appears on any portal page 4 hours after the employee signed in,
then every hour, until Midday is sent or skipped, or the employee signs out.
Closing it only hides it until the next hourly reminder. The reminder engine
decides when it is due (one ReminderDelivery per hour); this view only shows it.
"""

from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods, require_POST

from daily_updates import services as updates
from daily_updates.models import MIDDAY, MiddaySkip
from workspace_attendance import services as attendance
from workspace_attendance.adapters import get_adapter
from workspace_attendance.views import login_required
from workspace_reminders import engine
from workspace_reminders.models import ReminderDelivery

TEMPLATE = "workspace_reminders/midday_popup.html"


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
    delivery = _open_midday(employee) if employee else None
    if delivery is None:
        return HttpResponse("")
    return render(request, TEMPLATE, {"delivery": delivery, "text": ""})


@login_required
@require_POST
def close(request, delivery_id):
    employee = _employee(request)
    if employee:
        engine.acknowledge(employee, delivery_id)
    return HttpResponse("")


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
    try:
        updates.submit_update(employee, delivery.work_date, MIDDAY, {"summary": text}, "web")
    except attendance.WorkspaceError as error:
        return render(request, TEMPLATE, {"delivery": delivery, "text": text, "error": error.message})
    engine.acknowledge(employee, delivery.pk)
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
        return render(request, TEMPLATE, {"delivery": delivery, "error": error.message})
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
        return render(request, TEMPLATE, {"delivery": delivery, "error": error.message})
    engine.acknowledge(employee, delivery.pk)
    return _done(request, body.get("message") or _("Signed out at %(time)s.") % {"time": timezone.localtime().strftime("%H:%M")})
