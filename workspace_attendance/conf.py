"""
Settings for the Workspace sign-in and Daily Updates modules, with safe defaults.

Override any of them in Django settings, e.g. WORKSPACE_CORRECTION_WINDOW_DAYS = 14.
"""

from django.conf import settings

DEFAULTS = {
    # Dotted path of the adapter that connects Workspace to the HR system.
    "WORKSPACE_ADAPTER": "workspace_attendance.adapters.horilla.HorillaAdapter",
    # How many calendar days back an employee may fix their own times.
    "WORKSPACE_CORRECTION_WINDOW_DAYS": 30,
    # Workspace sign-outs and self-corrections count for payroll immediately
    # (narrowly scoped: only the Attendance rows Workspace touches).
    "WORKSPACE_AUTO_VALIDATE": True,
    # How long a desktop request's stored answer is kept and replayed. Older
    # answers are removed the next time that employee makes a keyed request.
    "WORKSPACE_IDEMPOTENCY_DAYS": 7,
    # Show the "Take a Break" button (right of "Away") on the Workspace card.
    "WORKSPACE_SHOW_BREAK": True,
}


def get(name):
    return getattr(settings, name, DEFAULTS[name])
