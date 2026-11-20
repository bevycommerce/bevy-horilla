from django.apps import AppConfig


class WorkspaceAttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workspace_attendance"
    verbose_name = "Workspace Attendance"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(path("workspace/", include("workspace_attendance.urls")))
        super().ready()
