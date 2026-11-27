# App map

Which app owns what. **Start here instead of grepping** — this repository has ~9,300 tracked files
across ~45 installed apps, and almost every feature already has a home.

The authoritative list of what is installed is `INSTALLED_APPS` in `horilla/settings/base.py`.
A route you cannot find in `horilla/urls.py` is appended from the app's own
`apps.py::ready()` ([ARCHITECTURE §3](../ARCHITECTURE.md#3-url-wiring-is-dynamic)).

## Bevy-only apps

These are ours. Changes here do not conflict with upstream.

| App | Owns | Detail |
|---|---|---|
| `workspace_attendance` | Workspace card, sign in / out, breaks, Away, Fix My Times self-correction, idempotency keys, correction log | [`WORKSPACE.md`](WORKSPACE.md) |
| `daily_updates` | Daily update submission, revisions, midday skips | [`WORKSPACE.md`](WORKSPACE.md) |
| `workspace_reminders` | Reminder delivery, snoozes, the reminder engine and its scheduler | [`WORKSPACE.md`](WORKSPACE.md) |
| `expense` | Employee expense submission | — |

Bevy additions **inside** upstream apps: the leave-approver chain (`leave/approvals.py`,
`leave/models.py::LeaveApprover`), the attendance break models and views
(`attendance/views/break_in_out.py`), `horilla/people_operations_preview.py` and `prototypes/`.
Keep these as small as possible —
[`compliance/keep-the-fork-mergeable.md`](../compliance/keep-the-fork-mergeable.md).

## Core HR domain

| App | Owns |
|---|---|
| `base` | Company, department, job position, job role, shift, work type, holidays, rotating shifts, announcements, the dashboards, the ESS dashboard, company middleware, the tenancy system check |
| `employee` | Employee, work info, contracts, the employee profile |
| `attendance` | Attendance, activities, validation, overtime, late/early rules, work records, breaks |
| `leave` | Leave types, requests, balances, approvals (including Bevy's approver chain), compensatory leave |
| `payroll` | Payslips, allowances, deductions, contracts, payroll run. `payroll/methods/` is a [protected path](../compliance/protected-paths.md) |
| `recruitment` | Recruitments, stages, candidates, the hiring pipeline |
| `onboarding` | New-hire onboarding tasks and portals |
| `offboarding` | Resignations and exit process |
| `pms` | Performance: objectives, key results, periods, feedback |
| `asset` | Asset categories, assignment, expiry notifications |
| `helpdesk` | Tickets, ticket types, department managers, FAQ |
| `project` | Projects, tasks, timesheets |
| `horilla_documents` | Document requests and employee documents |
| `master_import` | Spreadsheet import of employees, leave balances, assets and salary structures |
| `report` | Report templates, subscriptions, favourites, scheduled report email |

## Platform and framework apps

| App | Owns |
|---|---|
| `horilla_auth` | `HorillaUser`, authentication, password policy, two-factor |
| `horilla_views` | The generic class-based views every screen is built from, saved filters, column ordering, the history sidebar. See [`SCREENS.md`](SCREENS.md) |
| `horilla_widgets` | Shared form widgets and the AJAX choice endpoint behind `HorillaFilterSet.ajax_fields` |
| `horilla_theme` | Theme, colour themes, the asset bundle. `static/cdn/**` is vendored verbatim |
| `horilla_crumbs` | Breadcrumbs (context processor + the breadcrumb fragment route) |
| `horilla_audit` | Audit tags and the audit trail on top of `simple_history` / `auditlog` |
| `horilla_automations` | Mail automations: notifications on record create / update / delete |
| `horilla_api` | The DRF surface at `/api/v1/`, JWT auth, Swagger / ReDoc. See [`API.md`](API.md) |
| `horilla_backup` | Local and Google Drive database backups |
| `horilla_dbtemplate` | Database-backed template loader with host/domain resolution |
| `horilla_tour` | In-app product tours |
| `accessibility` | Per-feature accessibility rules and the middleware that applies them |
| `notifications` | Vendored `django-notifications` — database-backed in-app notifications and the bell tray. Excluded from `ruff` |

## Integrations and optional add-ons

| App | Owns | Enabled |
|---|---|---|
| `biometric` | Biometric attendance devices | Installed |
| `horilla_ldap` | LDAP directory sync and sign-in | Installed |
| `horilla_meet` | Google Meet and Google credentials | Installed |
| `whatsapp` | WhatsApp credentials and message flows | Installed |
| `geofencing` | Location-restricted attendance | In the repository, not enabled by default |
| `facedetection` | Face-recognition attendance | In the repository, not enabled by default |
| `outlook_auth` | Microsoft 365 / Azure mail | In the repository, not enabled by default |

Optional add-ons are gated by `check_integration_enabled` and by `horilla/settings/addons.py`, which
installs an app when its credentials are present.

## Directories that are not installed apps

| Path | What it is |
|---|---|
| `horilla/` | The Django project: settings package, root urlconf, `HorillaModel`, decorators, middleware, filters, scheduling registry, observability, the model/view inheritance machinery, the test kit |
| `prototypes/` | The People Operations static suite. [`PEOPLE_OPERATIONS.md`](PEOPLE_OPERATIONS.md) |
| `docker/` | `entrypoint.sh`, `gunicorn.conf.py`, `nginx.conf`, Docker Hub assets |
| `templates/`, `static/`, `media/` | Project-level templates, collected static, uploaded media |
| `auth/` | A single `login.html` override |
| `load_data/` | Demo-data JSON fixtures and avatars |
| `pg_backup/`, `dynamic_fields/` | Present in the tree but **not** in `INSTALLED_APPS` — do not build on them without checking why |
| `docs/` | These docs |

## Finding something not listed here

1. `python manage.py show_urls` is not installed; read `horilla/urls.py`, then grep `apps.py` for
   `urlpatterns.append`.
2. For a model: `grep -rn "class <Name>" --include=models.py`.
3. For a screen: grep the page title string — it is wrapped in `_("…")` in a `cbv/` module or a
   `sidebar.py`.
4. For a permission: `grep -rn "<app>.<perm>_<model>"`.

If this map sent you to the wrong place, fix the row and log it in
[`../navigation/MISSES.md`](../navigation/MISSES.md).
