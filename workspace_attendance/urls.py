from django.urls import path

from workspace_attendance import views

urlpatterns = [
    path("card/", views.workspace_card, name="workspace-card"),
    path("sign-in/", views.sign_in, name="workspace-sign-in"),
    path("sign-out/", views.sign_out, name="workspace-sign-out"),
    path("break/start/", views.break_start, name="workspace-break-start"),
    path("break/end/", views.break_end, name="workspace-break-end"),
    path("away/", views.away, name="workspace-away"),
    path("fix-times/", views.fix_times, name="workspace-fix-times"),
    path("fix-times/save/", views.fix_times_save, name="workspace-fix-times-save"),
]
