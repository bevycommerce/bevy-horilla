"""Reminder tables. State lives in the database so restarts never duplicate reminders."""

from django.db import models
from django.utils.translation import gettext_lazy as _

KIND_CHOICES = [
    ("sign_in", _("Sign in")),
    ("sign_in_followup", _("Sign in follow-up")),
    ("midday", _("Midday update")),
    ("eod", _("End-of-Day update")),
    ("sign_out", _("Sign out")),
]


class ReminderDelivery(models.Model):
    """One reminder sent to one employee. The unique constraint is the duplicate guard."""

    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE, related_name="workspace_reminders")
    work_date = models.DateField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    attempt = models.PositiveSmallIntegerField()
    due_at = models.DateTimeField()
    message = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    portal_notified = models.BooleanField(default=False)
    desktop_seen_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "work_date", "kind", "attempt"], name="reminder_once_per_attempt"
            )
        ]
        indexes = [models.Index(fields=["employee", "acknowledged_at"])]

    def __str__(self):
        return f"{self.employee_id} {self.work_date} {self.kind} #{self.attempt}"


class ReminderSnooze(models.Model):
    """Snooze of one reminder kind for one day. Fires once more at `until` if still needed."""

    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE, related_name="+")
    work_date = models.DateField()
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    until = models.DateTimeField()
    fired = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "work_date", "kind"], name="reminder_snooze_unique")
        ]
