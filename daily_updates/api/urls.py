"""Mounted at /api/workspace/v1/updates/."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.DayView.as_view(), name="ws-api-updates"),
    path("<int:update_id>/", views.EditView.as_view(), name="ws-api-update-edit"),
    path("midday-skip/", views.SkipView.as_view(), name="ws-api-midday-skip"),
]
