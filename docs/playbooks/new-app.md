# New Django app

## Goal

Add a Bevy capability as its own app, wired in the way every other app here is.

**Done when:** the app is installed, its routes and sidebar work, its migration is committed, and
the After checklist is complete.

## Before coding

- Read [`AGENTS.md`](../../AGENTS.md) and [`ARCHITECTURE.md`](../ARCHITECTURE.md) §3 (dynamic URL
  wiring) and §8 (the Bevy apps).
- **Justify the app.** A new app is right when the capability has its own models, its own screens
  and its own lifecycle — Workspace sign-in, Daily Updates and Reminders each do. It is wrong for a
  new screen over existing models, a new field, or a report: those extend the owning app
  ([`reference/APP_MAP.md`](../reference/APP_MAP.md)).
- Adding an app means editing `horilla/settings/base.py` (`INSTALLED_APPS`), which is a
  [protected path](../compliance/protected-paths.md). Say so in chat and keep the edit to that one
  list entry.
- Decide up front: the models, the permission that gates it, whether its data is company-scoped,
  and whether it needs a scheduled job.
- **Write the plan in chat. Wait for approval.**

## During coding

Copy the shape of `workspace_reminders` (small) or `daily_updates` (models + API + templates).

```
myapp/
  __init__.py
  apps.py              # AppConfig; appends urls to the root urlconf
  conf.py              # defaults, merged from Django settings
  models.py            # HorillaModel subclasses
  views.py             # function views / HTMX fragments
  cbv/                 # horilla_views generic screens
  forms.py             # base.forms subclasses
  filters.py           # HorillaFilterSet subclasses
  urls.py
  sidebar.py           # MENU / IMG_SRC / SUBMENUS
  scheduler.py         # register_job calls, if any
  signals.py           # receivers, imported from apps.py
  api/                 # serializers.py, views.py, urls.py
  templates/myapp/
  static/myapp/
  migrations/
  tests/
```

1. **AppConfig** mounts the routes and imports the signals:

   ```python
   class MyAppConfig(AppConfig):
       default_auto_field = "django.db.models.BigAutoField"
       name = "myapp"
       verbose_name = "My App"

       def ready(self):
           from django.conf import settings
           from django.urls import include, path

           from horilla.urls import urlpatterns

           from myapp import signals  # noqa: F401

           settings.APPS.append("myapp")
           urlpatterns.append(path("myapp/", include("myapp.urls")))
           super().ready()
   ```

   Mounting the routes in `horilla/urls.py` directly is also accepted — the three Workspace apps are
   mounted there. Pick one, not both.

2. **`INSTALLED_APPS`** — append after the Horilla apps, with a one-line comment saying what the app
   is for, as the Workspace block does.

3. **Config** goes in `myapp/conf.py` as a defaults dict merged from Django settings, so the app has
   one switchboard instead of scattered `getattr(settings, …)` calls
   (`workspace_attendance/conf.py` is the pattern).

4. **Models** extend `HorillaModel`, with `HorillaCompanyManager` if the data is per-company
   ([`compliance/company-scoping.md`](../compliance/company-scoping.md)).

5. **Screens** subclass the `horilla_views` generics
   ([`reference/SCREENS.md`](../reference/SCREENS.md)).

6. **Permissions** — Django creates `add_/change_/delete_/view_<model>` from the model. Decide which
   group or role gets them and say so in the PR
   ([`compliance/access-control.md`](../compliance/access-control.md)).

7. **Sidebar** — `MENU`, `IMG_SRC`, `SUBMENUS`, with an `accessibility` callable if not everyone
   sees it.

8. **API**, if the desktop or mobile client needs it — a module under the app plus a line in
   `horilla_api/urls.py`, following the `workspace/v1/` entries.

9. **Jobs**, if any — `register_job` in `myapp/scheduler.py`, never a scheduler instance
   ([`compliance/scheduled-jobs.md`](../compliance/scheduled-jobs.md)).

10. **Migration** — `python manage.py makemigrations myapp`, committed with the models.

## After coding

- Run the gate — `/hr-check`. `python manage.py check` catches a bad AppConfig;
  `check --tag horilla.tenancy` catches a missing company manager.
- `python manage.py test myapp`, with at least one test per model-level rule the app enforces.
- Click-test: the sidebar entry appears for the right role and not the wrong one; the list, create,
  edit and detail flows work; the API endpoint authenticates and is paginated.
- Add the app to [`reference/APP_MAP.md`](../reference/APP_MAP.md) and, if it is substantial, give it
  its own `reference/` file. Add its jobs to
  [`reference/SCHEDULED_JOBS.md`](../reference/SCHEDULED_JOBS.md) and its endpoints to
  [`reference/API.md`](../reference/API.md).
- Record why the app exists in [`DECISIONS.md`](../DECISIONS.md).
- Consider adding its label to `SMOKE_LABELS` in the `Makefile` once it has real tests.
