"""Mounted at /api/workspace/v1/ (see horilla_api/urls.py)."""

from django.urls import path

from . import views

urlpatterns = [
    path("status/", views.StatusView.as_view(), name="ws-api-status"),
    path("sign-in/", views.SignInView.as_view(), name="ws-api-sign-in"),
    path("sign-out/", views.SignOutView.as_view(), name="ws-api-sign-out"),
    path("break/start/", views.BreakStartView.as_view(), name="ws-api-break-start"),
    path("break/end/", views.BreakEndView.as_view(), name="ws-api-break-end"),
    path("away/", views.AwayView.as_view(), name="ws-api-away"),
    path("corrections/", views.CorrectionsView.as_view(), name="ws-api-corrections"),
]
