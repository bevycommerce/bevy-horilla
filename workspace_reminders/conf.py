"""Reminder settings. Override with settings.WORKSPACE_REMINDERS (merged per key)."""

from django.conf import settings

DEFAULTS = {
    "enabled": True,
    # A reminder is only sent within this many minutes after it became due
    # (prevents a flood of old reminders after the scheduler was offline).
    "stale_after_minutes": 60,
    # anchor: start / mid / end of the employee's shift; offset in minutes
    "kinds": {
        "sign_in": {"anchor": "start", "offset": 0, "attempts": 1, "repeat": 30},
        "sign_in_followup": {"anchor": "start", "offset": 30, "attempts": 1, "repeat": 30},
        "midday": {"anchor": "mid", "offset": 0, "attempts": 2, "repeat": 30},
        "eod": {"anchor": "end", "offset": -30, "attempts": 2, "repeat": 30},
        "sign_out": {"anchor": "end", "offset": 0, "attempts": 2, "repeat": 30},
    },
    "snooze_choices": [15, 30],
}


def get():
    custom = getattr(settings, "WORKSPACE_REMINDERS", {}) or {}
    merged = {**DEFAULTS, **{k: v for k, v in custom.items() if k != "kinds"}}
    kinds = {k: dict(v) for k, v in DEFAULTS["kinds"].items()}
    for kind, values in (custom.get("kinds") or {}).items():
        if kind in kinds:
            kinds[kind].update(values)
    merged["kinds"] = kinds
    return merged
