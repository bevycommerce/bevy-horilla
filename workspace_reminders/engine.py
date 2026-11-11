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


def due_time(window, kind_conf, signed_in_at=None):
    """When a reminder kind first becomes due. anchor "sign_in" counts from the sign-in time."""
    if kind_conf["anchor"] == "sign_in":
        if signed_in_at is None:
            return None
        return signed_in_at + timedelta(minutes=kind_conf["offset"])
    start, end = window
    anchor = {"start": start, "mid": start + (end - start) / 2, "end": end}[kind_conf["anchor"]]
    return anchor + timedelta(minutes=kind_conf["offset"])


def signed_in_at(employee, work_date, now, adapter):
    """First sign-in time of that work day (aware datetime) or None."""
    state = adapter.get_state(employee, now)
    if state["work_date"] == work_date and state["signed_in_at"]:
        return state["signed_in_at"]
    row = adapter.attendance_by_day(employee, work_date, work_date).get(work_date) or {}
    if row.get("sign_in"):
        from datetime import datetime

        return timezone.make_aware(datetime.combine(work_date, row["sign_in"]))
    return None


def _in_range(window, now):
    start, end = window
    # shift-based reminders are relevant from 1h before start until 2h after end
    return start - timedelta(hours=1) <= now <= end + timedelta(hours=2)


def _days(adapter, employee, now):
    """
    [(work_date, window or None, shift_ok)] that may need reminders right now.
    shift_ok: shift-based kinds may run (inside the shift range, not a day off).
    The current working day is always included, because sign-in based kinds
    (Midday) follow the sign-in time, not the shift (owner rule 2026-11-11).
    """
    days = {}
    for day in (now.date() - timedelta(days=1), now.date()):
        window = adapter.shift_window(employee, day)
        if window is not None and _in_range(window, now):
            days[day] = window
    state = adapter.get_state(employee, now)
    working_day = state["work_date"] if state["status"] in WORKING else None
    if working_day is not None and working_day not in days:
        days[working_day] = adapter.shift_window(employee, working_day)
    result = []
    for day, window in sorted(days.items()):
        shift_ok = window is not None and _in_range(window, now) and not adapter.is_day_off(employee, day)
        result.append((day, window, shift_ok))
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
        "midday": not midday_done and working_today,
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
    for work_date, window, shift_ok in _days(adapter, employee, now):
        need = needs(employee, work_date, now, adapter)
        started = signed_in_at(employee, work_date, now, adapter)
        snoozes = {s.kind: s for s in ReminderSnooze.objects.filter(employee=employee, work_date=work_date)}
        for kind, kind_conf in config["kinds"].items():
            if not need.get(kind):
                continue
            if kind_conf["anchor"] != "sign_in" and not shift_ok:
                continue
            first_due = due_time(window, kind_conf, started)
            if first_due is None:
                continue
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
    for work_date, window, shift_ok in _days(adapter, employee, now):
        need = needs(employee, work_date, now, adapter)
        started = signed_in_at(employee, work_date, now, adapter)
        for kind in ("sign_in", "midday", "eod", "sign_out"):
            due = due_time(window, config["kinds"][kind], started)
            if need.get(kind) and due is not None and due <= now:
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
