from django.apps import AppConfig


class WorkspaceAttendanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workspace_attendance"
    verbose_name = "Workspace Attendance"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        # ready() can run more than once (e.g. in tests): add the route only once
        if not any(str(getattr(p, "pattern", "")) == "workspace/" for p in urlpatterns):
            urlpatterns.append(path("workspace/", include("workspace_attendance.urls")))
        super().ready()
