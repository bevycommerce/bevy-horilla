"""
Web pages of the Daily Updates module.

Every rule (who may send what, late/backdated flags, edit history) lives in
daily_updates.services. These views only read the form, call a service, and
show its message or friendly error. They never decide what is allowed.

Company-wide pages use only data from the services, which expose just the safe
employee card (name, photo, department, job position).
"""

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_http_methods, require_POST

from daily_updates import services
from daily_updates.models import COMBINED, EOD, MIDDAY, DailyUpdate
from workspace_attendance.adapters import get_adapter
from workspace_attendance.views import login_required

logger = logging.getLogger(__name__)

RECENT_DAYS = 14
TYPE_CHOICES = [(MIDDAY, _lazy("Midday")), (EOD, _lazy("End of Day")), (COMBINED, _lazy("Combined"))]
TABS = ["today", "attendance", "updates", "history"]
GENERIC_ERROR = _lazy("Something went wrong. Please try again.")


def _employee(request):
    return get_adapter().get_employee(request.user)


def _is_htmx(request):
    return bool(request.headers.get("HX-Request")) and not request.headers.get("HX-Boosted")


def _parse_date(raw, label):
    """Returns (date or None, error). Empty input gives (None, "")."""
    raw = (raw or "").strip()
    if not raw:
        return None, ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date(), ""
    except ValueError:
        return None, _("%(label)s is not a valid date. Please pick a date from the calendar.") % {"label": label}


def _fields(request):
    return {name: request.POST.get(name, "") for name in services.TEXT_FIELDS}


# ---------------------------------------------------------------- my page
def _work_date(request, source):
    """The day being viewed: chosen date, or today. Returns (date, error)."""
    today = timezone.localdate()
    chosen, error = _parse_date(source.get("date"), _("The date"))
    if error:
        return today, error
    if chosen is None:
        return today, ""
    if chosen > today:
        return today, _("You cannot write an update for a future day.")
    return chosen, ""


def _recent_updates(employee):
    start = timezone.localdate() - timedelta(days=RECENT_DAYS - 1)
    return list(
        DailyUpdate.objects.filter(employee=employee, work_date__gte=start).order_by("-work_date", "-submitted_at")
    )


def _render_day(request, employee, work_date, message="", error="", regular=False, status=200, page=False, draft=None):
    today = timezone.localdate()
    recent = _recent_updates(employee)
    draft = draft if error else None  # only keep typed text when something failed
    for item in recent:
        item.draft = draft if draft and draft.get("update_id") == item.pk else None
    context = {
        "work_date": work_date,
        "is_today": work_date == today,
        "today": today,
        "oldest": today - timedelta(days=services.backdate_days()),
        "day": services.day_state(employee, work_date),
        "recent": recent,
        "drafts": {draft["type"]: draft} if draft and draft.get("type") else {},
        "regular": regular,
        "message": message,
        "error": error,
    }
    template = "daily_updates/my_updates.html" if page else "daily_updates/_my_day.html"
    return render(request, template, context, status=status)


@login_required
@require_http_methods(["GET", "HEAD"])
def my_updates(request):
    employee = _employee(request)
    if employee is None:
        return render(request, "daily_updates/my_updates.html", {"no_employee": True})
    work_date, error = _work_date(request, request.GET)
    part = request.GET.get("part") == "day"
    return _render_day(
        request, employee, work_date, error=error, regular=request.GET.get("regular") == "1", page=not part
    )


def _run(request, call, draft=None):
    """Run one service call for the posted day and re-render the day section."""
    employee = _employee(request)
    if employee is None:
        return HttpResponse("")
    work_date, error = _work_date(request, request.POST)
    if error:
        return _render_day(request, employee, work_date, error=error, draft=draft)
    message = ""
    try:
        _status, body = call(employee, work_date)
        message = body.get("message", "")
    except services.WorkspaceError as exc:
        error = exc.message
    except Exception:
        logger.exception("Daily update action failed")
        error = GENERIC_ERROR
    return _render_day(request, employee, work_date, message=message, error=error, draft=draft)


@login_required
@require_POST
def submit(request):
    update_type = request.POST.get("type", "")
    fields = _fields(request)
    key = request.POST.get("key", "")
    return _run(
        request,
        lambda e, d: services.submit_update(e, d, update_type, fields, "web", key=key),
        draft={"type": update_type, **fields},
    )


@login_required
@require_POST
def skip(request):
    choice = request.POST.get("choice", "")
    return _run(request, lambda e, d: services.skip_midday(e, d, choice, "web"))


@login_required
@require_POST
def edit(request, update_id):
    fields = _fields(request)
    return _run(
        request,
        lambda e, d: services.edit_update(e, update_id, fields, "web", actor=request.user),
        draft={"update_id": update_id, **fields},
    )


# ---------------------------------------------------------------- history
@login_required
@require_http_methods(["GET", "HEAD"])
def history(request, update_id):
    """Earlier versions of one update. Updates are company-visible, so anyone may read this."""
    update = DailyUpdate.objects.select_related("employee").filter(pk=update_id).first()
    context = {"update": None, "versions": [], "error": "", "embedded": _is_htmx(request)}
    status = 200
    if update is None:
        context["error"] = _("Update not found.")
        status = 200 if _is_htmx(request) else 404
    else:
        adapter = get_adapter()
        context.update(
            update=services.serialize_update(update),
            owner=adapter.safe_employee_card(update.employee),
            versions=services.update_history(update),
        )
        context["update"]["submitted_dt"] = update.submitted_at
        context["update"]["work_date_obj"] = update.work_date
        context["update"]["edited_dt"] = update.last_edited_at
        for version, revision in zip(context["versions"], update.revisions.all()):
            version["content_dt"] = revision.content_submitted_at
            version["replaced_dt"] = revision.replaced_at
    template = "daily_updates/_history.html" if _is_htmx(request) else "daily_updates/history_page.html"
    return render(request, template, context, status=status)


# ---------------------------------------------------------------- company dashboard
def _prepare_update(item):
    """Turn the ISO strings of a serialized update into dates/times the template can format."""
    item["work_date_obj"] = datetime.strptime(item["work_date"], "%Y-%m-%d").date()
    item["submitted_dt"] = datetime.fromisoformat(item["submitted_at"])
    item["edited_dt"] = datetime.fromisoformat(item["last_edited_at"]) if item["last_edited_at"] else None
    return item


def _company_filters(request):
    """Read and check the filters. Returns (filters dict, error message)."""
    data = request.GET
    today = timezone.localdate()
    errors = []
    tab = data.get("tab", "today")
    if tab not in TABS:
        tab = "today"

    department = data.get("dept", "").strip()
    department_id = int(department) if department.isdigit() else None
    update_type = data.get("type", "").strip()
    if update_type not in services.TYPES:
        update_type = ""

    day, err = _parse_date(data.get("date"), _("The date"))
    if err:
        errors.append(err)
    if day is None or day > today:
        if day is not None:
            errors.append(_("The date cannot be in the future. Showing today instead."))
        day = today

    default_start = today - timedelta(days=6) if tab == "history" else today
    start, err = _parse_date(data.get("from"), _("The From date"))
    if err:
        errors.append(err)
    end, err = _parse_date(data.get("to"), _("The To date"))
    if err:
        errors.append(err)
    start = start or default_start
    end = end or today
    if end > today:
        errors.append(_("The To date cannot be in the future. Showing up to today."))
        end = today
    if start > end:
        errors.append(_("The From date is after the To date. Showing the default dates instead."))
        start, end = default_start, today

    filters = {
        "tab": tab,
        "q": data.get("q", "").strip()[:100],
        "department_id": department_id,
        "type": update_type,
        "day": day,
        "start": start,
        "end": end,
    }
    return filters, " ".join(str(e) for e in errors)


def _query_string(filters, tab=None, keep_dates=True):
    params = {"tab": tab or filters["tab"]}
    if filters["q"]:
        params["q"] = filters["q"]
    if filters["department_id"]:
        params["dept"] = filters["department_id"]
    if filters["type"]:
        params["type"] = filters["type"]
    if keep_dates:
        if params["tab"] in ("today", "attendance"):
            params["date"] = filters["day"].isoformat()
        else:
            params["from"] = filters["start"].isoformat()
            params["to"] = filters["end"].isoformat()
    return urlencode(params)


def _company_context(request):
    filters, error = _company_filters(request)
    adapter = get_adapter()
    tab = filters["tab"]
    context = {
        "tab": tab,
        "f": filters,
        "error": error,
        "departments": adapter.departments(),
        "type_choices": TYPE_CHOICES,
        "tab_links": [
            (name, label, _query_string(filters, tab=name, keep_dates=False))
            for name, label in (
                ("today", _("Today")),
                ("attendance", _("Attendance")),
                ("updates", _("Work Updates")),
                ("history", _("History")),
            )
        ],
        "today": timezone.localdate(),
        "state_query": _query_string(filters),
        "rows": [],
        "feed": [],
        "totals": None,
        "limit_reached": False,
    }
    try:
        if tab in ("today", "attendance"):
            board = services.today_board(filters["day"], query=filters["q"] or None, department_id=filters["department_id"])
            context["totals"] = board["totals"]
            rows = []
            for row in board["rows"]:
                items = [row["updates"][t] for t in (MIDDAY, EOD, COMBINED) if t in row["updates"]]
                if filters["type"]:
                    items = [i for i in items if i["type"] == filters["type"]]
                    if not items:
                        continue
                row["update_list"] = [_prepare_update(i) for i in items]
                rows.append(row)
            context["rows"] = rows
        else:
            feed = services.company_feed(
                filters["start"],
                filters["end"],
                update_type=filters["type"] or None,
                query=filters["q"] or None,
                department_id=filters["department_id"],
            )
            for item in feed:
                _prepare_update(item["update"])
            context["feed"] = feed
            context["limit_reached"] = len(feed) >= 300
    except Exception:
        logger.exception("Company updates view failed")
        context["error"] = (context["error"] + " " + str(GENERIC_ERROR)).strip()
    return context


@login_required
@require_http_methods(["GET", "HEAD"])
def company(request):
    context = _company_context(request)
    return render(request, "daily_updates/company.html", context)


@login_required
@require_http_methods(["GET", "HEAD"])
def company_tab(request):
    context = _company_context(request)
    response = render(request, "daily_updates/_company_body.html", context)
    # keep the address bar in step so a reload or a shared link shows the same view
    response["HX-Push-Url"] = f"{reverse('daily-updates-company')}?{context['state_query']}"
    return response
