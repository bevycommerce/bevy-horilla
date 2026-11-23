# Workspace Sign-In and Daily Updates

This adds two features to the portal: one-click sign in and sign out from the dashboard, and short daily work updates that the whole company can read.

## Features

### My Workspace card (dashboard)
- **Start Your Day / Sign Out** in one click. It uses the same attendance records and the same rules as the header Check-In button (check-in setting, office network rule, night shifts, late come and early out).
- **Worked today** timer that keeps counting while the employee is signed in.
- **Take a Break**, shown to the right of **Away**. The employee picks a reason and can add an optional note. While on break:
  - the main timer is paused and marked "Paused";
  - the break's own length counts beside the reason;
  - **End Break** starts the timer again.
- **Away / I'm Back** marks the employee as away without stopping the work timer.
- **Sign In Again** after a sign out on the same day.
- The card refreshes every minute and when the tab is opened again, so a sign in done elsewhere shows without reloading the page.

### Fix My Times
- Employees can correct their own sign-in and sign-out times for the last 30 days.
- Every change is kept in a history log: old time, new time, who changed it and when.
- Overtime still needs HR approval. A day whose overtime HR has already approved cannot be self-corrected in a way that changes that overtime; HR changes those times.

### Break Log (Attendance menu)
- Lists every break with its reason, note, start, end and length.
- Admins and users with the view attendance permission see everyone; other employees see only their own breaks.
- **Export CSV** downloads the dates chosen; **Export All (CSV)** downloads every date. Cells that start with `=`, `+`, `-` or `@` are prefixed so a spreadsheet never runs them as formulas.

### Daily Updates (new menu)
- **My Updates**
  - Midday update ("What are you working on?").
  - End of Day update ("What did you do today?").
  - Optional details for each.
  - **Skip Midday**: write the note later, or combine Midday and End of Day into one update.
  - Edit an update; earlier versions are kept for the author.
  - Delete an update; it is removed completely, including its earlier versions.
- **Company Updates**, with four tabs:
  - **Today**: who is working, on break, signed out or not signed in, plus today's updates.
  - **Attendance**
  - **Work Updates**
  - **History**

  It can be filtered by name, department, date and update type. Only safe fields are shown: no salary, phone or other private data.

### API for a desktop app (optional)
- These endpoints sit under `/api/workspace/v1/`:
  - `status/`, `sign-in/`, `sign-out/`, `break/start/`, `break/end/`, `away/`, `corrections/`
  - `updates/`, `updates/<id>/`, `updates/midday-skip/`
- They use a Bearer JWT (the portal's existing simplejwt setup); a missing or expired token answers 401.
- Every write needs an `Idempotency-Key` header, so a retried request never signs in twice.
- An employee can only act on their own records.

## Architecture

```
attendance/                     (existing app, additions only)
  models.py                     + AttendanceBreak, EmployeePresence
  migrations/0004_...           new tables for the two models
  services/breaks.py            Break and Away rules, no HTTP request needed
  views/break_log.py            Break Log page and CSV export
workspace_attendance/           new app: card, Fix My Times, API
  adapters/base.py              the methods the Workspace needs from an HR system
  adapters/horilla.py           the only module that talks to Horilla attendance models;
                                reuses clock_in_attendance_and_activity, late_come,
                                early_out and overtime_calculation from attendance
  services.py                   sign in/out, breaks, away, corrections, idempotency, audit
  views.py, templates/          the card (HTMX) and the Fix My Times page
  api/                          REST endpoints (DRF + simplejwt)
  models.py                     WorkspaceAttendanceMeta, WorkspaceAttendanceEvent,
                                AttendanceCorrectionLog, WorkspaceIdempotencyKey
daily_updates/                  new app: Daily Updates pages, company feed, API
  models.py                     DailyUpdate, DailyUpdateRevision, MiddaySkip
  services.py                   submit, skip, combine, edit, delete rules
  views.py, templates/, api/
```

- **One rule set for every route:** the web card, the Fix My Times page and the API call the same service functions.
- **No new settings and no new packages:** the apps are registered in `horilla/horilla_apps.py`, the URLs are added from each app's `ready()` (the same way `recruitment` does it), and the API is added in `horilla_api/urls.py`.
- **Database:** three committed migrations, which only add new tables:
  - `attendance/0004`
  - `workspace_attendance/0001`
  - `daily_updates/0001`
- **Optional settings** (with defaults):
  - `WORKSPACE_CORRECTION_WINDOW_DAYS` (30)
  - `WORKSPACE_AUTO_VALIDATE` (True: Workspace sign-outs and self-corrections are validated so they count for payroll)
  - `WORKSPACE_SHOW_BREAK` (True)
  - `WORKSPACE_IDEMPOTENCY_DAYS` (7: how long a desktop request can be retried and get its first answer back)
  - `ATTENDANCE_TRUSTED_PROXIES` (unset: a list of proxy addresses or networks whose `X-Forwarded-For` is trusted for the office network rule; when unset, private and loopback proxies are trusted)
