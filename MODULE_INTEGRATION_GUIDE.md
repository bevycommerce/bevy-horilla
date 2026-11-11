# Module Integration Guide: Smart Employee Workspace

How to reuse the Smart Employee Workspace in another Django HR portal.

The Workspace is three Django apps plus a desktop app:

| Part | Folder | What it does | Depends on |
|---|---|---|---|
| Workspace attendance | `workspace_attendance/` | One-click sign in/out, Fix My Times, audit log, duplicate protection, homepage card, attendance API, **the adapter** | Django, DRF, SimpleJWT (for the API) |
| Daily Updates | `daily_updates/` | Midday / End-of-Day / Combined updates, Midday skip, edit history, company dashboard, updates API | `workspace_attendance` |
| Reminders | `workspace_reminders/` | Shift-based reminders, snooze, pending actions, reminders API | `workspace_attendance`, `daily_updates`, a scheduler |
| Desktop Companion | `desktop-companion/` | Electron tray app (Windows first) talking to the API | The API only |

Only one file talks to the HR system: **`workspace_attendance/adapters/horilla.py`**. Moving to another portal means writing a replacement adapter. The rest stays as is.

---

## 1. Requirements in the target portal

- Django 5.x, PostgreSQL (row locks `SELECT ... FOR UPDATE` are used to prevent double clicks racing; tested on PostgreSQL 16).
- Django REST Framework and a JWT login API for the desktop app (Horilla uses `djangorestframework-simplejwt`). Any token auth works if `request.user` is set.
- An employee record linked to the login user.
- An attendance store with daily records (or the ability to write one).
- A background scheduler that can run one function every 2 minutes (APScheduler, Celery Beat, cron calling a management command, etc.).
- A notification centre is optional (adapter `notify()` may return False).
- HTMX on the pages if you reuse the web templates (the card and pages use `hx-get` / `hx-post`).

## 2. Copy and register

1. Copy the three folders into the project.
2. Add to `INSTALLED_APPS`: `"workspace_attendance"`, `"daily_updates"`, `"workspace_reminders"`.
3. URLs:
   ```python
   # web pages
   path("workspace/", include("workspace_attendance.urls")),
   path("daily-updates/", include("daily_updates.urls")),
   # API (under your API prefix, e.g. /api/)
   path("workspace/v1/updates/", include("daily_updates.api.urls")),
   path("workspace/v1/reminders/", include("workspace_reminders.api_urls")),
   path("workspace/v1/", include("workspace_attendance.api.urls")),
   ```
   The more specific `updates/` and `reminders/` lines must come before the general `workspace/v1/` line.
4. Run migrations (section 5).
5. Put the card on a homepage: `{% include "workspace_attendance/workspace_card_host.html" %}`.
6. Add a menu entry for `daily-updates` (My Updates) and `daily-updates-company` (Company Updates). In Horilla this is `daily_updates/sidebar.py` plus `SIDEBARS`.
7. Schedule `workspace_reminders.engine.run_reminders` every 2 minutes and `workspace_attendance.services.cleanup_idempotency_keys` once a day. In Horilla this is `workspace_reminders/scheduler.py` (via `horilla.scheduling.register_job`). For other schedulers, call the same two functions. The job is safe to run twice at the same time.

## 3. Write the adapter

Create a class that implements `workspace_attendance/adapters/base.py::BaseAdapter`, then set:

```python
WORKSPACE_ADAPTER = "myportal.workspace_adapter.MyPortalAdapter"
```

| Method | Must do |
|---|---|
| `get_employee(user)` | Return the employee for a user, or None (no employee means no Workspace). |
| `safe_employee_card(employee)` | Return only `{id, name, photo, department_id, department, job_position}`. Everything here is shown to all employees, so never add private data. |
| `departments()`, `active_employees(query, department_id)` | Lists for the company dashboard and reminders. |
| `get_state(employee, now)` | Return status (`not_signed_in`, `working`, `away`, `on_break`, `signed_out`), work_date, signed-in/out times, worked_seconds, timer_running, break, away_since. |
| `check_allowed(employee, client_ip, coords)` | Raise `AttendanceActionError` when your company rules forbid a sign in/out (feature off, IP, location). |
| `sign_in(employee, now)`, `sign_out(employee, now)` | Use your portal's own sign in/out logic and return the day record. Do not duplicate business rules here; call your existing code. |
| `start_break`, `end_break`, `set_away`, `clear_away` | Optional features; may raise `AttendanceActionError` if unsupported. |
| `correct_times(employee, work_date, sign_in, sign_out, now)` | Change or create the day's times and recompute worked hours / late / early the way your portal does. Return `(record, [(field, old, new), ...])`. |
| `mark_valid_for_payroll(record)` | Make the record count for payroll (Horilla: `attendance_validated=True`). Only called for records the Workspace touched. |
| `attendance_by_day(employee, start, end)` | `{date: {sign_in, sign_out, worked}}` |
| `attendance_overview(day, employees, now)` | Rows for the company Today/Attendance tabs (see the Horilla adapter for the exact keys). |
| `shift_window(employee, day)` | `(start_datetime, end_datetime)` or None when not working that day. Drives reminders and late Midday. |
| `is_day_off(employee, day)` | True on holidays, company off days and approved leave (no reminders). |
| `notify(employee, message, url)` | Put a message in your notification centre; return False if you have none. |
| `break_reasons()` | `[{value, label}]` (empty list if no breaks). |

Start by copying `adapters/horilla.py` and replacing the Horilla imports. The tests in `workspace_attendance/tests/` show exactly what the adapter must support. Rewrite `tests/helpers.py` to create an employee, shift and company in your portal, then run all Workspace tests.

**Payroll check (important):** run `workspace_attendance/tests/test_services.py::PayrollCompatibilityTests` adapted to your payroll. A Workspace day must count exactly like an HR-approved day, and records the Workspace never touched must keep your existing rules.

## 4. Settings

| Setting | Default | Meaning |
|---|---|---|
| `WORKSPACE_ADAPTER` | Horilla adapter | Which adapter to use |
| `WORKSPACE_CORRECTION_WINDOW_DAYS` | 30 | Fix My Times window |
| `WORKSPACE_AUTO_VALIDATE` | True | Workspace sign-outs and corrections count for payroll immediately |
| `WORKSPACE_SHOW_BREAK` | False | Start-break button on the card and desktop app |
| `WORKSPACE_UPDATE_BACKDATE_DAYS` | 30 | How far back Daily Updates may be sent |
| `WORKSPACE_MIDDAY_LATE_AFTER_MINUTES` | 60 | Grace after shift midpoint for Midday |
| `WORKSPACE_REMINDERS` | see `workspace_reminders/conf.py` | `enabled`, `stale_after_minutes`, per-kind `anchor/offset/attempts/repeat`, `snooze_choices` |
| `WORKSPACE_IDEMPOTENCY_DAYS` | 7 | How long retry keys are remembered |
| `TIME_ZONE`, `USE_TZ=True` | (project) | All Workspace dates follow the project time zone; Horilla runs with `Asia/Dhaka` |

No URL, employee id or credential is hardcoded in the modules.

## 5. Database migrations

All migrations only **create new tables**. They never change or delete existing HR tables.

| App | Migration | Tables |
|---|---|---|
| workspace_attendance | `0001_initial` | `workspace_attendance_workspaceattendancemeta`, `..._workspaceattendanceevent`, `..._attendancecorrectionlog`, `..._workspaceidempotencykey` |
| daily_updates | `0001_initial` | `daily_updates_dailyupdate`, `..._dailyupdaterevision`, `..._middayskip` |
| workspace_reminders | `0001_initial` | `workspace_reminders_reminderdelivery`, `..._remindersnooze` |

The migrations reference the HR models through foreign keys (`employee.Employee`, `attendance.Attendance`, `settings.AUTH_USER_MODEL`). In another portal, edit those references in the three `0001_initial.py` files (and the matching `models.py` fields) to point at your employee and attendance models before the first `migrate`. In Horilla, `workspace_attendance 0001` depends on `attendance 0017` (the owner's break/Away migration).

To remove the Workspace later: unregister the apps and drop the tables above. HR data is unaffected.

## 6. Authentication for the desktop app

The desktop app needs three endpoints in the target portal:
- `POST /api/auth/login/` with username and password, returning an access and a refresh token,
- `POST /api/auth/refresh/`,
- `POST /api/auth/logout/`.

If the portal uses another login API, change only `desktop-companion/src/core/` (the API client) and the Workspace API views' authentication class. All Workspace API views extend `workspace_attendance.api.views.WorkspaceAPIView`, so one change there covers every endpoint.

## 7. Desktop Companion setup

See `desktop-companion/README.md`. In short:
- Employees install it once, enter the portal address, log in.
- The portal must be reachable from their computers over HTTPS. A `localhost` server only works on the computer running it.
- Set `appId`, `productName` and icons in `desktop-companion/package.json` for another company.
- Windows notification buttons need the installed version (Start Menu shortcut). Code signing is recommended to avoid security warnings.
- macOS must be built, signed and notarized on a Mac with an Apple Developer account (not yet tested).

## 8. Checklist after integrating

- [ ] `manage.py check` and `makemigrations --check` are clean
- [ ] All Workspace tests pass with the new adapter and helpers
- [ ] The portal's own attendance and payroll tests still pass
- [ ] Sign in/out on the card and in the desktop app, check the day in the HR attendance pages
- [ ] Fix a past day, check worked hours, late/early flags and payroll
- [ ] Company dashboard shows only name, photo, department, job position and work notes
- [ ] Reminder job runs once per interval; no duplicate notifications after restarting the scheduler
