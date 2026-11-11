from django.urls import path

from daily_updates import views

urlpatterns = [
    path("", views.my_updates, name="daily-updates"),
    path("submit/", views.submit, name="daily-updates-submit"),
    path("skip/", views.skip, name="daily-updates-skip"),
    path("edit/<int:update_id>/", views.edit, name="daily-updates-edit"),
    path("history/<int:update_id>/", views.history, name="daily-updates-history"),
    path("company/", views.company, name="daily-updates-company"),
    path("company/tab/", views.company_tab, name="daily-updates-company-tab"),
]
