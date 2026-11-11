"""
Settings for the Smart Workspace modules, with safe defaults.

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
    # How long a stored idempotency key is kept.
    "WORKSPACE_IDEMPOTENCY_DAYS": 7,
    # Show the "Take a Break" button on the Workspace card and desktop app.
    # Off by owner decision (2026-11-11). The header break feature is not affected,
    # and a break started there is still shown on the card with "End Break".
    "WORKSPACE_SHOW_BREAK": False,
}


def get(name):
    return getattr(settings, name, DEFAULTS[name])
