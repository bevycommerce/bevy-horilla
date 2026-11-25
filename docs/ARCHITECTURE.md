# Architecture

The system map. Short by design — each section links to the detail. Agents arrive here from
[`AGENTS.md`](../AGENTS.md); read the section you need, not the file.

## 1. What this is

Bevy's internal HR portal: a fork of Horilla HRMS v2 (Django 5.2) with three Bevy-only apps added.
Employees use it to sign in and out, log daily updates, request leave and expenses, and read their
own records; HR uses it for the full employee lifecycle, attendance validation and payroll.

| Piece | Value |
|---|---|
| Framework | Django 5.2, Python 3.12 |
| Database | PostgreSQL 16 |
| Cache | Redis 7 (cache only, via `django-redis`) — no Celery, no Channels |
| Web server | gunicorn behind nginx (`docker/gunicorn.conf.py`, `docker/nginx.conf`) |
| Background jobs | APScheduler in one dedicated process, `manage.py run_scheduler` |
| Front end | Django templates + HTMX + the `horilla_theme` asset bundle. No SPA build for the HR app |
| API | DRF + SimpleJWT at `/api/v1/` (and the deprecated `/api/` alias) |
| Deployed at | https://hr-portal.bevy.dev from branch `staging` |

## 2. Request path

```
nginx → gunicorn → Django MIDDLEWARE → urlconf → view → template/JSON
```

The middleware stack (`horilla/settings/base.py`, `MIDDLEWARE`) is ordered deliberately and each
entry's comment says why. The ones that change how your code behaves:

| Middleware | Effect on your code |
|---|---|
| `horilla.observability.RequestIDMiddleware` | First, so every log line in the request carries a correlation id. |
| `horilla.horilla_middlewares.ThreadLocalMiddleware` | Puts `request` in thread locals. `HorillaModel.save()` reads it to set `created_by` / `modified_by`. |
| `base.middleware.CompanyMiddleware` | Resolves the selected company into a `ContextVar` that `HorillaCompanyManager` filters on. **Does not run for API calls** — see [§4](#4-multi-company-tenancy). |
| `base.middleware.ForcePasswordChangeMiddleware`, `TwoFactorAuthMiddleware` | Can redirect any request before your view runs. |
| `accessibility.middlewares.AccessibilityMiddleware` | Applies per-feature accessibility rules. |
| `axes.middleware.AxesMiddleware` | Last; turns the Axes backend's `PermissionDenied` into the lockout response. |

## 3. URL wiring is dynamic

`horilla/urls.py` mounts only a handful of apps directly. **Most apps append their own routes to the
root urlconf from `AppConfig.ready()`**:

```python
# leave/apps.py
def ready(self):
    from horilla.urls import urlpatterns
    settings.APPS.append("leave")
    urlpatterns.append(path("leave/", include("leave.urls")))
```

So a route you cannot find in `horilla/urls.py` lives in `<app>/apps.py`. The API is mounted the
same way from `horilla_api/apps.py`, at both `/api/v1/` and `/api/`.

Mounted directly in `horilla/urls.py`: `base`, `employee`, `expense`, `workspace_attendance`
(`/workspace/`), `workspace_reminders` (`/workspace/reminders/`), `daily_updates`
(`/daily-updates/`), `master_import`, `horilla_views`, `horilla_audit`, `horilla_automations`,
`horilla_tour`, `horilla_widgets`, notifications, `/health/`, `/ready/`, `/metrics/`, and the People
Operations prototype at `/people-ops/`, `/hr/`, `/expenses/`, `/insurance/`.

## 4. Multi-company tenancy

Records are scoped to a `Company`. `base/horilla_company_manager.py::HorillaCompanyManager` filters
querysets by the company in the request context, which `CompanyMiddleware` sets.

The gap that bites: **middleware runs before DRF resolves a JWT**, so it sees `AnonymousUser` and
returns early, leaving API queries unscoped. That is why the API authenticates through
`horilla_api.authentication.TenantScopedJWTAuthentication`, which sets the ContextVar itself. Any new
authentication class must do the same.

`python manage.py check --tag horilla.tenancy` (`base/checks.py`) warns about models that look
company-scoped but are not. Rule: [`compliance/company-scoping.md`](compliance/company-scoping.md).
Test helpers: `horilla/testkit/company.py`.

## 5. Models

Almost every first-party model extends `horilla.models.HorillaModel`, which adds `created_at`,
`created_by`, `modified_by`, `is_active`, an `auditlog` history field, and an **XSS check on every
save**. `HorillaModel.save()` calls `clean_fields()` directly — not `full_clean()` — because code
written while validation was disabled relies on saves that `full_clean()` would reject. Read the
comment in `horilla/models.py` before touching that method; it records two CVE bypasses.

Model-level extension across apps goes through `horilla/inherit/` (`_inherit`, an injection registry
and a custom migration autodetector that routes injected fields into the extending app's
migrations). Use it instead of editing an upstream model in place —
[`compliance/keep-the-fork-mergeable.md`](compliance/keep-the-fork-mergeable.md).

## 6. Screens

HR screens are not hand-written pages. They subclass the generic class-based views in
`horilla_views/generic/cbv/views.py`:

| Class | Role |
|---|---|
| `HorillaListView` | The table: `columns`, `sortby_mapping`, `filter_class`, bulk actions, export |
| `HorillaNavView` | The toolbar above it: title, search, create button, filter panel, actions |
| `HorillaFormView` | Create / edit in a modal, with add / change permission mixins |
| `HorillaDetailedView` | The detail modal: `header` + `body` field lists |
| `HorillaCardView`, `HorillaTabView`, `HorillaSectionView`, `HorillaProfileView` | Card grids, tab shells, composed sections, the employee profile |

Each is wired as its own URL (list, nav, form, detail are separate routes) and composed in the
browser with HTMX attributes. Worked example and the cookbook:
[`reference/SCREENS.md`](reference/SCREENS.md). Rule:
[`compliance/screens-use-horilla-views.md`](compliance/screens-use-horilla-views.md).

Navigation comes from two places: a per-app `<app>/sidebar.py` (`MENU`, `IMG_SRC`, `SUBMENUS`, each
entry optionally with an `accessibility` callable and `match_prefixes`), and the settings menu
registry in `horilla/menu/`.

## 7. Background jobs

One process owns execution: `manage.py run_scheduler`, running as the `scheduler` container.
Jobs register themselves at import time:

```python
from horilla.scheduling import register_job
register_job(my_job, "interval", hours=4)
```

`horilla/scheduling.py` explains the defect this replaced: every `<app>/scheduler.py` used to start
its own `BackgroundScheduler()` at import time, so with `preload_app = False` and up to 8 gunicorn
workers, payroll generation and database backups ran up to 8 times per interval with no lock. Never
reintroduce that. Rule: [`compliance/scheduled-jobs.md`](compliance/scheduled-jobs.md). Inventory:
[`reference/SCHEDULED_JOBS.md`](reference/SCHEDULED_JOBS.md).

`/ready/` reports scheduler status but does not fail on it unless `HORILLA_REQUIRE_SCHEDULER=1` —
a 503 there would pull web out of the load balancer over a delayed job.

## 8. The Bevy-only apps

Three apps are ours, not upstream's. They are the **Smart Employee Workspace**.

| App | Owns |
|---|---|
| `workspace_attendance` | Sign in / out, breaks, Away, "Fix My Times" self-correction, the workspace card |
| `daily_updates` | Daily update submission, revisions, midday skips |
| `workspace_reminders` | Reminder delivery and snoozes, driven by its own engine + scheduler |

The governing design decision: **Workspace never stores its own attendance times.** It calls
Horilla's `clock_in_attendance_and_activity()` / `clock_out_attendance_and_activity()` and keeps only
metadata — events, idempotency keys, correction logs. Full design, settings and API:
[`reference/WORKSPACE.md`](reference/WORKSPACE.md). Rule:
[`compliance/workspace-attendance-integrity.md`](compliance/workspace-attendance-integrity.md).

`expense/` is also a Bevy addition, and `leave/approvals.py` plus `leave/models.py::LeaveApprover`
carry Bevy's leave-approver chain.

## 9. People Operations prototype

A static front-end suite under `prototypes/bevy-people-operations-suite/`, served to signed-in
staging users by `horilla/people_operations_preview.py` at `/people-ops/`, `/hr/`, `/expenses/` and
`/insurance/`. **It uses fictional data and is not wired to the HR database.** It has its own
allowlist of servable files and its own CI job — the only workflow that runs on `staging` PRs.
Detail: [`reference/PEOPLE_OPERATIONS.md`](reference/PEOPLE_OPERATIONS.md).

## 10. API

DRF at `/api/v1/` (`/api/` is a deprecated alias kept for existing clients). Auth is SimpleJWT:
60-minute access token, 30-day refresh, rotation with blacklist, and password change revokes tokens.
Login is throttled. Swagger at `/api/v1/swagger/`, ReDoc at `/api/v1/redoc/` — public only when
`DEBUG`, admin-only otherwise.

Surfaces: one module per Horilla app, a `mobile/` group of screen-shaped aggregates for the mobile
client, and `workspace/v1/` for the desktop companion. Detail:
[`reference/API.md`](reference/API.md), and [`workspace_api.md`](workspace_api.md) for the Workspace
contract.

## 11. Environments

| Environment | Where | Branch |
|---|---|---|
| Staging (the live internal portal) | https://hr-portal.bevy.dev, compose project `horilla-v2` | `staging` |
| Production (v1, not yet migrated) | separate host, v1 database | `1.0` line |
| Local | `make dev` | your branch |

Staging is already v2 with the v1 data copied in. Production has **not** moved. The cutover plan,
including what must not be done to a v1 database, is [`v1-to-v2.md`](v1-to-v2.md); the operational
picture is [`reference/ENVIRONMENTS.md`](reference/ENVIRONMENTS.md).

---

> **Didn't find what you came here for?** Log it in [`navigation/MISSES.md`](navigation/MISSES.md).
