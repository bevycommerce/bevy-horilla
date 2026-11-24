"""Daily Updates tables."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from workspace_attendance.models import SOURCE_CHOICES

MIDDAY = "midday"
EOD = "eod"
COMBINED = "combined"
UPDATE_TYPES = [
    (MIDDAY, _("Midday Update")),
    (EOD, _("End-of-Day Update")),
    (COMBINED, _("Combined Midday + End-of-Day Update")),
]


class DailyUpdate(models.Model):
    employee = models.ForeignKey(
        "employee.Employee", on_delete=models.PROTECT, related_name="daily_updates"
    )
    work_date = models.DateField()
    update_type = models.CharField(max_length=10, choices=UPDATE_TYPES)
    summary = models.TextField(max_length=5000)
    completed = models.TextField(max_length=3000, blank=True, default="")
    ongoing = models.TextField(max_length=3000, blank=True, default="")
    blockers = models.TextField(max_length=3000, blank=True, default="")
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="web")
    submitted_at = models.DateTimeField(auto_now_add=True)
    last_edited_at = models.DateTimeField(null=True, blank=True)
    revision_count = models.PositiveIntegerField(default=0)
    is_late = models.BooleanField(default=False)

    class Meta:
        ordering = ["-work_date", "-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "work_date", "update_type"],
                name="daily_update_one_per_type_per_day",
            )
        ]
        indexes = [models.Index(fields=["work_date", "update_type"])]

    @property
    def is_backdated(self):
        from django.utils import timezone

        return timezone.localtime(self.submitted_at).date() > self.work_date

    @property
    def is_edited(self):
        return self.revision_count > 0

    def __str__(self):
        return f"{self.employee_id} {self.work_date} {self.update_type}"


class DailyUpdateRevision(models.Model):
    """Previous content of an edited update. Append-only."""

    update = models.ForeignKey(DailyUpdate, on_delete=models.CASCADE, related_name="revisions")
    revision_number = models.PositiveIntegerField()
    summary = models.TextField()
    completed = models.TextField(blank=True, default="")
    ongoing = models.TextField(blank=True, default="")
    blockers = models.TextField(blank=True, default="")
    content_submitted_at = models.DateTimeField()
    replaced_at = models.DateTimeField(auto_now_add=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="web")

    class Meta:
        ordering = ["-revision_number"]
        constraints = [
            models.UniqueConstraint(fields=["update", "revision_number"], name="daily_update_revision_unique")
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("Update revisions cannot be changed.")
        super().save(*args, **kwargs)


class MiddaySkip(models.Model):
    """
    The employee's explicit choice to skip the Midday Update for a day.
    This is NOT an update: nothing is shown as submitted because of it.
    """

    LATER = "later"
    COMBINE = "combine"
    CHOICES = [
        (LATER, _("Write Midday note later")),
        (COMBINE, _("Combine Midday with End of Day")),
    ]

    employee = models.ForeignKey("employee.Employee", on_delete=models.CASCADE, related_name="midday_skips")
    work_date = models.DateField()
    choice = models.CharField(max_length=10, choices=CHOICES)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="web")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["employee", "work_date"], name="midday_skip_one_per_day")
        ]

    def __str__(self):
        return f"{self.employee_id} {self.work_date} skip: {self.choice}"
