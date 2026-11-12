from django.urls import path
from django.views.generic import RedirectView

from daily_updates import views

urlpatterns = [
    # "mine/" so the sidebar (which highlights by path prefix) does not also
    # mark My Updates as active on /daily-updates/company/
    path("", RedirectView.as_view(pattern_name="daily-updates", query_string=True), name="daily-updates-root"),
    path("mine/", views.my_updates, name="daily-updates"),
    path("submit/", views.submit, name="daily-updates-submit"),
    path("skip/", views.skip, name="daily-updates-skip"),
    path("edit/<int:update_id>/", views.edit, name="daily-updates-edit"),
    path("delete/<int:update_id>/", views.delete, name="daily-updates-delete"),
    path("history/<int:update_id>/", views.history, name="daily-updates-history"),
    path("company/", views.company, name="daily-updates-company"),
    path("company/tab/", views.company_tab, name="daily-updates-company-tab"),
]
