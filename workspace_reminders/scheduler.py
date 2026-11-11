"""Registers the reminder job with Horilla's single scheduler process (manage.py run_scheduler)."""

from horilla.scheduling import register_job


def _run_reminders():
    from workspace_reminders.engine import run_reminders

    run_reminders()


def _cleanup_keys():
    from workspace_attendance.services import cleanup_idempotency_keys

    cleanup_idempotency_keys()


register_job(_run_reminders, "interval", job_id="workspace_reminders.run", minutes=2)
register_job(_cleanup_keys, "cron", job_id="workspace_attendance.cleanup_idempotency_keys", hour=3, minute=17)
