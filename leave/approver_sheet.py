"""
leave/approver_sheet.py

Reads the project approvers Google Sheet (owner decision 2026-11-13).

One row per project. The columns are found by their headings:
  - Project Name  -> heading contains "project" (and not "manager"/"pm")
  - PM column(s)  -> heading is "PM", "PMs", "PM/PMs" or contains "project manager"
  - Everyone else named in the row (for example the "Emails" and
    "Developer/Software Engineer" columns) is a project member.
A cell may hold several people, separated by commas, semicolons or new lines.
People are matched to portal employees by email first, then by full name.

Settings (from the environment / .env, never from git):
  LEAVE_APPROVER_SHEET_ID        the sheet id from its link (.../d/<id>/edit)
  LEAVE_APPROVER_SHEET_RANGE     optional, default "A:Z" of the first tab, or "Tab name!A:Z"
  LEAVE_APPROVER_SHEET_KEY_FILE  path to the Google service-account key (json)
  LEAVE_APPROVER_SHEET_CACHE_SECONDS  optional, default 600

The sheet stays private: it is shared (Viewer) with the service account's email.
"""

import logging
import os
import re

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_KEY = "leave:approver_sheet:v1"
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SPLIT_RE = re.compile(r"[,;\n/]+")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class SheetUnavailable(Exception):
    """The sheet could not be used. The message is shown to the HR Lead."""


def _setting(name, default=""):
    value = getattr(settings, name, None)
    if value in (None, ""):
        value = os.environ.get(name, default)
    return value


def is_configured():
    return bool(_setting("LEAVE_APPROVER_SHEET_ID")) and bool(_setting("LEAVE_APPROVER_SHEET_KEY_FILE"))


def _fetch_rows():
    """Raw rows (lists of strings) from Google. Raises SheetUnavailable."""
    sheet_id = _setting("LEAVE_APPROVER_SHEET_ID")
    key_file = _setting("LEAVE_APPROVER_SHEET_KEY_FILE")
    sheet_range = _setting("LEAVE_APPROVER_SHEET_RANGE", "A:Z") or "A:Z"
    if not sheet_id or not key_file:
        raise SheetUnavailable("the approvers sheet is not set up in the portal yet")
    if not os.path.exists(key_file):
        raise SheetUnavailable("the Google key file for the approvers sheet is missing on the server")
    try:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_file(key_file, scopes=SCOPES)
        session = AuthorizedSession(creds)
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_range}"
        response = session.get(url, params={"majorDimension": "ROWS"}, timeout=10)
    except Exception as exc:  # network, bad key file, ...
        logger.warning("Approver sheet could not be read: %s", exc.__class__.__name__)
        raise SheetUnavailable("the approvers sheet could not be reached") from exc
    if response.status_code == 403:
        raise SheetUnavailable("the approvers sheet is not shared with the portal's Google account")
    if response.status_code == 404:
        raise SheetUnavailable("the approvers sheet was not found (check the sheet id and tab name)")
    if response.status_code != 200:
        raise SheetUnavailable(f"Google answered with an error ({response.status_code}) for the approvers sheet")
    return response.json().get("values", [])


def _people(cell):
    """Split one cell into people: [('email', x) | ('name', x)]."""
    out = []
    for part in SPLIT_RE.split(cell or ""):
        part = part.strip()
        if not part:
            continue
        emails = EMAIL_RE.findall(part)
        if emails:
            out.extend(("email", e.lower()) for e in emails)
        else:
            out.append(("name", " ".join(part.lower().split())))
    return out


def _is_pm_heading(heading):
    h = re.sub(r"[^a-z/ ]", "", heading.lower()).strip()
    if "project manager" in h:
        return True
    words = set(re.split(r"[ /]+", h))
    return bool(words & {"pm", "pms"})


def _is_project_heading(heading):
    h = heading.lower()
    return "project" in h and "manager" not in h and not _is_pm_heading(heading)


def parse_rows(rows):
    """
    Rows -> list of projects: {"project": str, "members": [...], "pms": [...]}.
    Raises SheetUnavailable when no PM column can be found.
    """
    if not rows:
        raise SheetUnavailable("the approvers sheet is empty")
    headings = [str(h or "") for h in rows[0]]
    pm_cols = [i for i, h in enumerate(headings) if _is_pm_heading(h)]
    if not pm_cols:
        raise SheetUnavailable("no PM column was found in the approvers sheet (a heading like 'PM/PMs' is needed)")
    project_cols = [i for i, h in enumerate(headings) if _is_project_heading(h)]
    projects = []
    for row in rows[1:]:
        cells = [str(c or "") for c in row]
        if not any(c.strip() for c in cells):
            continue
        name = next((cells[i].strip() for i in project_cols if i < len(cells) and cells[i].strip()), "")
        pms, members = [], []
        for i, cell in enumerate(cells):
            if i in project_cols:
                continue
            (pms if i in pm_cols else members).extend(_people(cell))
        projects.append({"project": name or "a project", "members": members, "pms": pms})
    return projects


def load_projects(force=False):
    """
    Parsed projects, cached for a few minutes so a leave request does not wait
    on Google every time. Raises SheetUnavailable.
    """
    if not force:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return cached
    projects = parse_rows(_fetch_rows())
    seconds = int(_setting("LEAVE_APPROVER_SHEET_CACHE_SECONDS", "600") or 600)
    cache.set(CACHE_KEY, projects, seconds)
    return projects


def _key(employee):
    email = (getattr(employee, "email", "") or "").strip().lower()
    user = getattr(employee, "employee_user_id", None)
    login_email = (getattr(user, "email", "") or "").strip().lower() if user else ""
    name = " ".join(f"{employee.employee_first_name or ''} {employee.employee_last_name or ''}".lower().split())
    return {e for e in (email, login_email) if e}, name


def _matches(person, emails, name):
    kind, value = person
    return value in emails if kind == "email" else bool(name) and value == name


def _find_employee(person):
    from employee.models import Employee

    kind, value = person
    active = Employee.objects.filter(is_active=True)
    if kind == "email":
        found = active.filter(email__iexact=value).first()
        return found or active.filter(employee_user_id__email__iexact=value).first()
    for employee in active.filter(employee_first_name__iexact=value.split(" ")[0]):
        if _key(employee)[1] == value:
            return employee
    return None


def sheet_approvers(employee):
    """
    (approvers, problems) for this employee from the sheet.
    approvers: [(Employee, "PM of <project>")]; problems: list of messages for HR.
    Raises SheetUnavailable when the sheet itself cannot be used, or the
    employee is not in it.
    """
    projects = load_projects()
    emails, name = _key(employee)
    approvers, problems, seen_projects = [], [], []
    for project in projects:
        if not any(_matches(p, emails, name) for p in project["members"]):
            continue
        seen_projects.append(project["project"])
        if not project["pms"]:
            problems.append(f"no PM is listed for {project['project']} in the approvers sheet")
        for pm in project["pms"]:
            person = _find_employee(pm)
            if person is None:
                problems.append(
                    f"the PM '{pm[1]}' of {project['project']} in the approvers sheet does not match any active employee in the portal"
                )
            else:
                approvers.append((person, f"PM of {project['project']}"))
    if not seen_projects:
        raise SheetUnavailable("this employee's email was not found in the approvers sheet")
    return approvers, problems


def clear_cache():
    cache.delete(CACHE_KEY)

