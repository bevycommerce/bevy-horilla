"""Mounted at /api/workspace/v1/reminders/."""

from django.urls import path

from . import api

urlpatterns = [
    path("", api.RemindersView.as_view(), name="ws-api-reminders"),
    path("<int:delivery_id>/snooze/", api.SnoozeView.as_view(), name="ws-api-reminder-snooze"),
    path("<int:delivery_id>/ack/", api.AckView.as_view(), name="ws-api-reminder-ack"),
]
