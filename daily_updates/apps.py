from django.apps import AppConfig


class DailyUpdatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "daily_updates"
    verbose_name = "Daily Updates"

    def ready(self):
        from django.urls import include, path

        from horilla.urls import urlpatterns

        urlpatterns.append(path("daily-updates/", include("daily_updates.urls")))
        super().ready()
