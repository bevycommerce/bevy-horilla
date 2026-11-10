"""
Daily Updates business rules (plan D9).

- Midday is optional. Skip stores a choice (LATER or COMBINE), never a fake update.
- At the end of the day the employee can send: a regular EOD, the pending Midday
  note (marked late), or ONE combined note.
- A combined note is a single record and can never coexist with a separate
  Midday or EOD for the same day (and the reverse), so nothing is duplicated.
- Every update keeps its work date and its real submission time separately.
- Editing keeps every previous version.
"""

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from daily_updates.models import COMBINED, EOD, MIDDAY, DailyUpdate, DailyUpdateRevision, MiddaySkip
from workspace_attendance.adapters import get_adapter
from workspace_attendance.services import (
    WorkspaceError,
    _check_source,
    _lock_employee,
    run_idempotent,
)

TYPES = {MIDDAY, EOD, COMBINED}
TEXT_FIELDS = ("summary", "completed", "ongoing", "blockers")
LIMITS = {"summary": 5000, "completed": 3000, "ongoing": 3000, "blockers": 3000}


def backdate_days():
    return getattr(settings, "WORKSPACE_UPDATE_BACKDATE_DAYS", 30)


def midday_late_after_minutes():
    return getattr(settings, "WORKSPACE_MIDDAY_LATE_AFTER_MINUTES", 60)


# ----------------------------------------------------------------- helpers
def _clean_fields(fields):
    cleaned = {}
    for name in TEXT_FIELDS:
        value = (fields.get(name) or "").strip()
        if len(value) > LIMITS[name]:
            raise WorkspaceError(
                _("%(field)s is too long (maximum %(max)s characters).") % {"field": name.title(), "max": LIMITS[name]},
                code="too_long",
            )
        cleaned[name] = value
    if not cleaned["summary"]:
        raise WorkspaceError(_("Please write a short note about your work."), code="empty")
    return cleaned


def _check_work_date(work_date):
    today = timezone.localdate()
    if work_date > today:
        raise WorkspaceError(_("You cannot send an update for a future day."), code="future")
    if work_date < today - timedelta(days=backdate_days()):
        raise WorkspaceError(
            _("Updates can be sent for the last %(days)s days only.") % {"days": backdate_days()},
            code="outside_window",
        )


def _midday_deadline(employee, work_date):
    window = get_adapter().shift_window(employee, work_date)
    if window is None:
        return timezone.make_aware(timezone.datetime.combine(work_date, timezone.datetime.min.time())) + timedelta(hours=14)
    start, end = window
    return start + (end - start) / 2 + timedelta(minutes=midday_late_after_minutes())


def _is_late(employee, work_date, update_type, now, skip):
    if update_type == MIDDAY:
        return bool(skip and skip.choice == MiddaySkip.LATER) or now > _midday_deadline(employee, work_date)
    return now.date() > work_date


def day_state(employee, work_date):
    """What exists for a day and what the employee can still send."""
    updates = {u.update_type: u for u in DailyUpdate.objects.filter(employee=employee, work_date=work_date)}
    skip = MiddaySkip.objects.filter(employee=employee, work_date=work_date).first()
    has_combined = COMBINED in updates
    return {
        "work_date": work_date,
        "midday": updates.get(MIDDAY),
        "eod": updates.get(EOD),
        "combined": updates.get(COMBINED),
        "skip": skip,
        "can_submit_midday": not has_combined and MIDDAY not in updates,
        "can_skip_midday": not has_combined and MIDDAY not in updates and EOD not in updates,
        "can_submit_eod": not has_combined and EOD not in updates,
        "can_submit_combined": not updates,
        "recommend_combined": bool(skip and skip.choice == MiddaySkip.COMBINE and not updates),
        "midday_pending_later": bool(skip and skip.choice == MiddaySkip.LATER and MIDDAY not in updates and not has_combined),
        "carry_forward": updates[MIDDAY].ongoing if MIDDAY in updates else "",
    }


def serialize_update(update):
    return {
        "id": update.pk,
        "work_date": update.work_date.isoformat(),
        "type": update.update_type,
        "type_label": str(update.get_update_type_display()),
        "summary": update.summary,
        "completed": update.completed,
        "ongoing": update.ongoing,
        "blockers": update.blockers,
        "submitted_at": timezone.localtime(update.submitted_at).isoformat(),
        "last_edited_at": timezone.localtime(update.last_edited_at).isoformat() if update.last_edited_at else None,
        "is_late": update.is_late,
        "is_backdated": update.is_backdated,
        "is_edited": update.is_edited,
        "source": update.source,
    }


def serialize_day(state):
    return {
        "work_date": state["work_date"].isoformat(),
        "midday": serialize_update(state["midday"]) if state["midday"] else None,
        "eod": serialize_update(state["eod"]) if state["eod"] else None,
        "combined": serialize_update(state["combined"]) if state["combined"] else None,
        "skip": state["skip"].choice if state["skip"] else None,
        **{k: state[k] for k in (
            "can_submit_midday", "can_skip_midday", "can_submit_eod", "can_submit_combined",
            "recommend_combined", "midday_pending_later", "carry_forward",
        )},
    }


# ----------------------------------------------------------------- actions
def submit_update(employee, work_date, update_type, fields, source, key=""):
    _check_source(source)
    if update_type not in TYPES:
        raise WorkspaceError(_("Unknown update type."), code="bad_type")
    _check_work_date(work_date)
    cleaned = _clean_fields(fields)

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            existing = set(
                DailyUpdate.objects.filter(employee=employee, work_date=work_date).values_list("update_type", flat=True)
            )
            if update_type in existing:
                raise WorkspaceError(
                    _("You already sent this update for this day. You can edit it instead."),
                    code="duplicate", status=409,
                )
            if update_type in (MIDDAY, EOD) and COMBINED in existing:
                raise WorkspaceError(
                    _("You already sent one combined update for this day. Edit that update instead."),
                    code="combined_exists", status=409,
                )
            if update_type == COMBINED and existing:
                raise WorkspaceError(
                    _("You already sent a separate update for this day, so a combined update is not possible. Send the End-of-Day update instead."),
                    code="separate_exists", status=409,
                )
            now = timezone.localtime()
            skip = MiddaySkip.objects.filter(employee=employee, work_date=work_date).first()
            update = DailyUpdate.objects.create(
                employee=employee,
                work_date=work_date,
                update_type=update_type,
                source=source,
                is_late=_is_late(employee, work_date, update_type, now, skip),
                **cleaned,
            )
            return 201, {
                "ok": True,
                "message": _("Update sent."),
                "update": serialize_update(update),
                "day": serialize_day(day_state(employee, work_date)),
            }

    return run_idempotent(employee, key, f"update_{update_type}", do)


def edit_update(employee, update_id, fields, source, actor, key=""):
    _check_source(source)
    cleaned = _clean_fields(fields)

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            update = DailyUpdate.objects.select_for_update().filter(pk=update_id).first()
            if update is None or update.employee_id != employee.pk:
                # same answer for "missing" and "someone else's": no information leak
                raise WorkspaceError(_("Update not found."), code="not_found", status=404)
            if all(getattr(update, f) == cleaned[f] for f in TEXT_FIELDS):
                return 200, {"ok": True, "message": _("Nothing changed."), "update": serialize_update(update)}
            DailyUpdateRevision.objects.create(
                update=update,
                revision_number=update.revision_count + 1,
                content_submitted_at=update.last_edited_at or update.submitted_at,
                edited_by=actor,
                source=source,
                **{f: getattr(update, f) for f in TEXT_FIELDS},
            )
            for f in TEXT_FIELDS:
                setattr(update, f, cleaned[f])
            update.revision_count += 1
            update.last_edited_at = timezone.now()
            update.save()
            return 200, {"ok": True, "message": _("Update saved."), "update": serialize_update(update)}

    return run_idempotent(employee, key, "update_edit", do)


def skip_midday(employee, work_date, choice, source, key=""):
    _check_source(source)
    if choice not in (MiddaySkip.LATER, MiddaySkip.COMBINE):
        raise WorkspaceError(_("Choose Write later or Combine with End of Day."), code="bad_choice")
    _check_work_date(work_date)

    def do():
        with transaction.atomic():
            _lock_employee(employee)
            state = day_state(employee, work_date)
            if state["midday"] or state["combined"]:
                raise WorkspaceError(_("Your Midday note for this day is already sent."), code="already_sent", status=409)
            if choice == MiddaySkip.COMBINE and state["eod"]:
                raise WorkspaceError(
                    _("Your End-of-Day update is already sent, so it cannot be combined. You can still write the Midday note later."),
                    code="eod_exists", status=409,
                )
            MiddaySkip.objects.update_or_create(
                employee=employee, work_date=work_date, defaults={"choice": choice, "source": source}
            )
            message = (
                _("Midday skipped. You can write it any time from Daily Updates.")
                if choice == MiddaySkip.LATER
                else _("Midday skipped. At the end of the day you will write one combined note.")
            )
            return 200, {"ok": True, "message": message, "day": serialize_day(day_state(employee, work_date))}

    return run_idempotent(employee, key, f"skip_{choice}", do)


def update_history(update):
    return [
        {
            "revision": r.revision_number,
            "summary": r.summary,
            "completed": r.completed,
            "ongoing": r.ongoing,
            "blockers": r.blockers,
            "content_submitted_at": timezone.localtime(r.content_submitted_at).isoformat(),
            "replaced_at": timezone.localtime(r.replaced_at).isoformat(),
        }
        for r in update.revisions.all()
    ]


# ----------------------------------------------------------------- company-wide views
def company_feed(start, end, update_type=None, query=None, department_id=None, limit=300):
    """
    Everyone's submitted updates (company-wide visibility is intentional).
    Each row holds only the safe employee card plus the update itself.
    """
    adapter = get_adapter()
    employees = {e.pk: e for e in adapter.active_employees(query=query, department_id=department_id)}
    updates = DailyUpdate.objects.filter(employee_id__in=list(employees), work_date__range=(start, end))
    if update_type in TYPES:
        updates = updates.filter(update_type=update_type)
    return [
        {"employee": adapter.safe_employee_card(employees[u.employee_id]), "update": serialize_update(u)}
        for u in updates.order_by("-work_date", "-submitted_at")[:limit]
    ]


def today_board(day, query=None, department_id=None):
    """Attendance status plus that day's updates for every active employee, and totals."""
    adapter = get_adapter()
    employees = adapter.active_employees(query=query, department_id=department_id)
    rows = adapter.attendance_overview(day, employees)
    updates = {}
    for u in DailyUpdate.objects.filter(employee_id__in=[e.pk for e in employees], work_date=day):
        updates.setdefault(u.employee_id, {})[u.update_type] = serialize_update(u)
    skips = dict(
        MiddaySkip.objects.filter(employee_id__in=[e.pk for e in employees], work_date=day).values_list(
            "employee_id", "choice"
        )
    )
    totals = {"working": 0, "on_break": 0, "signed_out": 0, "not_signed_in": 0, "late": 0, "missing": 0, "updates": 0}
    for row in rows:
        emp_id = row["employee"]["id"]
        row["updates"] = updates.get(emp_id, {})
        row["midday_skip"] = skips.get(emp_id)
        totals[row["status"]] += 1
        totals["late"] += int(row["late"])
        totals["missing"] += int(bool(row["missing"]))
        totals["updates"] += len(row["updates"])
    return {"day": day.isoformat(), "rows": rows, "totals": totals, "employee_count": len(rows)}
