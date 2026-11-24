"""
Workspace attendance tables.

None of these store attendance times of their own: Horilla's Attendance and
AttendanceActivity stay the single source of truth. These tables only keep
the extra facts the Workspace needs (who did what, from where, when the
server recorded it, and duplicate protection).
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

SOURCE_CHOICES = [
    ("web", _("Web portal")),
    ("desktop", _("Desktop companion")),
    ("api", _("API")),
]


class WorkspaceAttendanceMeta(models.Model):
    """Marks an Attendance row that the Workspace created or changed."""

    attendance = models.OneToOneField(
        "attendance.Attendance",
        on_delete=models.CASCADE,
        related_name="workspace_meta",
    )
    managed_by_workspace = models.BooleanField(default=True)
    last_source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    last_corrected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Workspace meta for attendance {self.attendance_id}"


class WorkspaceAttendanceEvent(models.Model):
    """
    One attendance action. reported_time is what the employee says happened,
    recorded_at is the server clock when it was saved.
    """

    ACTION_CHOICES = [
        ("sign_in", _("Sign in")),
        ("sign_out", _("Sign out")),
        ("break_start", _("Break start")),
        ("break_end", _("Break end")),
        ("away", _("Away")),
        ("back", _("Back from away")),
        ("correction", _("Time correction")),
    ]

    employee = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="workspace_attendance_events",
    )
    attendance = models.ForeignKey(
        "attendance.Attendance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workspace_events",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    work_date = models.DateField()
    reported_time = models.DateTimeField()
    recorded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    idempotency_key = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-recorded_at", "-id"]
        indexes = [models.Index(fields=["employee", "work_date"])]

    def __str__(self):
        return f"{self.employee_id} {self.action} {self.reported_time}"


class AttendanceCorrectionLog(models.Model):
    """
    Immutable history of Fix My Times changes. Rows can be added but never
    edited or deleted through Django.
    """

    FIELD_CHOICES = [
        ("sign_in", _("Sign in")),
        ("sign_out", _("Sign out")),
        ("created", _("Day created")),
    ]

    employee = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        related_name="workspace_correction_logs",
    )
    attendance = models.ForeignKey(
        "attendance.Attendance",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workspace_correction_logs",
    )
    work_date = models.DateField()
    field = models.CharField(max_length=10, choices=FIELD_CHOICES)
    old_value = models.CharField(max_length=40, blank=True, default="")
    new_value = models.CharField(max_length=40, blank=True, default="")
    recorded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    idempotency_key = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-recorded_at", "-id"]

    def save(self, *args, **kwargs):
        if self.pk is not None and not kwargs.pop("_allow_update", False):
            raise ValueError("AttendanceCorrectionLog rows cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("AttendanceCorrectionLog rows cannot be deleted.")

    def __str__(self):
        return f"{self.employee_id} {self.work_date} {self.field}: {self.old_value} -> {self.new_value}"


class WorkspaceIdempotencyKey(models.Model):
    """
    Remembers the answer to a request carrying an Idempotency-Key, so a retried
    click (for example from the desktop app after a network drop) is applied once.
    """

    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.CASCADE, related_name="+"
    )
    key = models.CharField(max_length=64)
    action = models.CharField(max_length=40)
    status_code = models.PositiveSmallIntegerField(default=200)
    response = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "key"], name="ws_idempotency_unique_per_employee"
            )
        ]

    def __str__(self):
        return f"{self.employee_id} {self.action} {self.key}"
