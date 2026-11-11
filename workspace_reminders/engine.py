"""
Reminder engine (plan D11).

run_reminders() is the single scheduled job. For every active employee with a
shift today (and yesterday's night shift), it checks which reminders are due
and not yet needed-no-more, and records a ReminderDelivery BEFORE notifying.
The database unique constraint (employee, work_date, kind, attempt) makes the
job idempotent: running it twice, or in two processes, sends each reminder once.

Rules:
- No reminders on holidays, company leave days or approved leave.
- A reminder stops as soon as its action is done.
- Explicit Midday skip stops only Midday reminders; EOD and Sign Out continue.
- Snooze (15/30 min) suppresses that kind until the snooze ends, then fires once more if still needed.
- Reminders older than stale_after_minutes are not sent (no flood after downtime).
"""

import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from daily_updates.services import day_state
from workspace_attendance.adapters import get_adapter
from workspace_reminders import conf
from workspace_reminders.models import ReminderDelivery, ReminderSnooze

logger = logging.getLogger(__name__)

WORKING = ("working", "away", "on_break")


def messages():
    return {
        "sign_in": _("Good morning. Do not forget to sign in."),
        "sign_in_followup": _("You have not signed in yet today. Sign in with one click."),
        "midday": _("Time for a quick Midday update. You can also skip it."),
        "eod": _("Your day ends soon. Please write your End-of-Day update."),
        "sign_out": _("Your shift has ended. Remember to sign out."),
    }


def due_time(window, kind_conf):
    start, end = window
    anchor = {"start": start, "mid": start + (end - start) / 2, "end": end}[kind_conf["anchor"]]
    return anchor + timedelta(minutes=kind_conf["offset"])


def _windows(adapter, employee, now):
    """(work_date, (start, end)) pairs that may need reminders right now."""
    result = []
    for day in (now.date() - timedelta(days=1), now.date()):
        window = adapter.shift_window(employee, day)
        if window is None:
            continue
        start, end = window
        # relevant from 1h before start until 2h after end
        if start - timedelta(hours=1) <= now <= end + timedelta(hours=2):
            result.append((day, window))
    return result


def needs(employee, work_date, now, adapter=None):
    """Which reminder kinds are still needed for this employee and day (ignores timing)."""
    adapter = adapter or get_adapter()
    state = adapter.get_state(employee, now)
    rows = adapter.attendance_by_day(employee, work_date, work_date)
    signed_in = bool(rows.get(work_date, {}).get("sign_in")) or (
        state["status"] in WORKING and state["work_date"] == work_date
    )
    working_today = state["status"] in WORKING and state["work_date"] == work_date
    updates = day_state(employee, work_date)
    midday_done = bool(updates["midday"] or updates["combined"] or updates["skip"])
    eod_done = bool(updates["eod"] or updates["combined"])
    return {
        "sign_in": not signed_in,
        "sign_in_followup": not signed_in,
        "midday": not midday_done,
        "eod": not eod_done,
        "sign_out": working_today,
    }


def _deliver(adapter, employee, work_date, kind, attempt, due_at, message):
    try:
        with transaction.atomic():
            delivery = ReminderDelivery.objects.create(
                employee=employee, work_date=work_date, kind=kind, attempt=attempt, due_at=due_at, message=message
            )
    except IntegrityError:
        return None  # already sent (another run got there first)
    try:
        from django.urls import reverse

        url = reverse("daily-updates") if kind in ("midday", "eod") else "/"
    except Exception:
        url = "/"
    try:
        if adapter.notify(employee, message, url=url):
            ReminderDelivery.objects.filter(pk=delivery.pk).update(portal_notified=True)
    except Exception:  # a notification failure must not stop other reminders
        logger.exception("Portal notification failed for reminder %s", delivery.pk)
    return delivery


def process_employee(employee, now, adapter=None, config=None):
    """Send what is due for one employee. Returns the list of new deliveries."""
    adapter = adapter or get_adapter()
    config = config or conf.get()
    stale = timedelta(minutes=config["stale_after_minutes"])
    texts = messages()
    sent = []
    for work_date, window in _windows(adapter, employee, now):
        if adapter.is_day_off(employee, work_date):
            continue
        need = needs(employee, work_date, now, adapter)
        snoozes = {s.kind: s for s in ReminderSnooze.objects.filter(employee=employee, work_date=work_date)}
        for kind, kind_conf in config["kinds"].items():
            if not need.get(kind):
                continue
            first_due = due_time(window, kind_conf)
            snooze = snoozes.get(kind)
            if snooze is not None and snooze.until > now:
                continue
            if snooze is not None and not snooze.fired:
                # snooze ended: one more reminder. Snooze re-fires are numbered 101, 102, ...
                attempt = 101 + ReminderDelivery.objects.filter(
                    employee=employee, work_date=work_date, kind=kind, attempt__gt=100
                ).count()
                delivery = _deliver(adapter, employee, work_date, kind, attempt, snooze.until, texts[kind])
                ReminderSnooze.objects.filter(pk=snooze.pk).update(fired=True)
                if delivery:
                    sent.append(delivery)
                continue
            if snooze is not None:
                continue  # snoozed once and already re-fired; no more scheduled repeats today
            for attempt in range(kind_conf["attempts"], 0, -1):
                due = first_due + timedelta(minutes=kind_conf["repeat"] * (attempt - 1))
                if due <= now:
                    if now - due <= stale:
                        delivery = _deliver(adapter, employee, work_date, kind, attempt, due, texts[kind])
                        if delivery:
                            sent.append(delivery)
                    break  # only the latest due attempt is considered
    return sent


def run_reminders(now=None):
    """The scheduled job. Safe to run any number of times."""
    config = conf.get()
    if not config["enabled"]:
        return 0
    adapter = get_adapter()
    now = now or timezone.localtime()
    total = 0
    for employee in adapter.active_employees():
        try:
            total += len(process_employee(employee, now, adapter, config))
        except Exception:
            logger.exception("Reminder check failed for employee %s", employee.pk)
    return total


# ----------------------------------------------------------------- employee-facing
def snooze(employee, delivery_id, minutes):
    config = conf.get()
    if minutes not in config["snooze_choices"]:
        raise ValueError("Snooze must be one of %s minutes." % config["snooze_choices"])
    delivery = ReminderDelivery.objects.filter(pk=delivery_id, employee=employee).first()
    if delivery is None:
        return None
    until = timezone.now() + timedelta(minutes=minutes)
    ReminderSnooze.objects.update_or_create(
        employee=employee,
        work_date=delivery.work_date,
        kind=delivery.kind,
        defaults={"until": until, "fired": False},
    )
    delivery.acknowledged_at = timezone.now()
    delivery.save(update_fields=["acknowledged_at"])
    return until


def acknowledge(employee, delivery_id):
    return ReminderDelivery.objects.filter(
        pk=delivery_id, employee=employee, acknowledged_at__isnull=True
    ).update(acknowledged_at=timezone.now())


def open_reminders(employee, now=None):
    """Unacknowledged reminders from today/yesterday whose action is still needed (for the desktop app)."""
    now = now or timezone.localtime()
    adapter = get_adapter()
    result = []
    cache = {}
    for delivery in ReminderDelivery.objects.filter(
        employee=employee, acknowledged_at__isnull=True, work_date__gte=now.date() - timedelta(days=1)
    ).order_by("created_at"):
        if delivery.work_date not in cache:
            cache[delivery.work_date] = needs(employee, delivery.work_date, now, adapter)
        if not cache[delivery.work_date].get(delivery.kind):
            continue
        result.append(delivery)
    return result


def pending_actions(employee, now=None):
    """Live list of what the employee still has to do today (homepage Pending Actions)."""
    now = now or timezone.localtime()
    adapter = get_adapter()
    config = conf.get()
    labels = {
        "sign_in": _("Sign in for today"),
        "midday": _("Write or skip your Midday update"),
        "eod": _("Write your End-of-Day update"),
        "sign_out": _("Sign out"),
    }
    actions = []
    for work_date, window in _windows(adapter, employee, now):
        if adapter.is_day_off(employee, work_date):
            continue
        need = needs(employee, work_date, now, adapter)
        for kind in ("sign_in", "midday", "eod", "sign_out"):
            if need.get(kind) and due_time(window, config["kinds"][kind]) <= now:
                actions.append({"kind": kind, "label": str(labels[kind]), "work_date": work_date.isoformat()})
    # forgotten sign outs on earlier days that can still be fixed
    from workspace_attendance.services import recent_days

    for day in recent_days(employee, days=7):
        if day["missing_sign_out"]:
            actions.append(
                {
                    "kind": "fix_sign_out",
                    "label": str(_("Add your missing sign out for %(day)s") % {"day": day["date"].strftime("%d %b")}),
                    "work_date": day["date"].isoformat(),
                }
            )
    return actions
