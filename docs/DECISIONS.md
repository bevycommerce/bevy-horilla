# Decisions

Calls that have already been made, so a change does not quietly reverse one. **Check the rows for
the area you are touching before you plan.** If your plan contradicts one, say which in chat before
coding.

Each row links to where the decision is enforced, which is also where its full reasoning lives.
A decision is not a rule — rules are in [`compliance/`](compliance/README.md).

Add a row when a call is made that someone would otherwise re-litigate or accidentally undo. Keep it
to one line plus a "why"; the detail belongs next to the code.

## Workspace and attendance

| # | Decision | Why | Where |
|---|---|---|---|
| D-01 | Workspace never stores its own attendance times; it calls Horilla's clock-in/out functions and keeps metadata only | One source of truth. Two clocks diverge, and payroll reads Horilla's | [`reference/WORKSPACE.md`](reference/WORKSPACE.md), `WORKSPACE_IMPLEMENTATION_PLAN.md` D1 |
| D-02 | A Workspace sign-out or self-correction sets `attendance_validated=True` on **that row only**; the global validation rule and HR's pages are untouched | Employees need their times to count immediately with no approval, without changing policy for every other record | `WORKSPACE_AUTO_VALIDATE`, [`reference/WORKSPACE.md`](reference/WORKSPACE.md) |
| D-03 | Overtime approval stays an HR decision — Workspace never sets `attendance_overtime_approve` | Base pay can be self-served; overtime pay cannot. Disclosed in the UI | same |
| D-04 | Self-correction window is 30 calendar days, no future times | Long enough for a forgotten day, short enough that a closed payroll period is not reopened | `WORKSPACE_CORRECTION_WINDOW_DAYS` |
| D-05 | `WorkspaceAttendanceEvent` is append-only, with both `reported_time` and `recorded_at` | The employee's claim and the server's clock are different facts, and neither may be edited afterwards | `workspace_attendance/models.py::AppendOnlyQuerySet` |
| D-06 | Every mutating Workspace API call needs an `Idempotency-Key`; a repeat replays the stored response | A desktop client retrying must not double-clock someone | `WorkspaceIdempotencyKey` |
| D-07 | The "Take a Break" button is off on the card; a break started from the header still shows there | Owner decision, 11 Nov 2026 | `WORKSPACE_SHOW_BREAK` |
| D-08 | Horilla's green check-in/out timer is hidden in the top bar | Owner rule, 12 Nov 2026 — the Workspace card is the one place to sign in and out | `WORKSPACE_HIDE_HEADER_CLOCK` |
| D-09 | The Midday reminder arrives 4 h after **sign-in**, then hourly until the update is sent or skipped or the employee signs out | Owner rule, 11 Nov 2026. Anchored to sign-in, not to the shift, because people start at different times | `workspace_reminders/conf.py` |
| D-10 | A reminder is only delivered within `stale_after_minutes` of becoming due | The scheduler coming back online must not flood everyone with yesterday's reminders | same |
| D-11 | Leave approvers always include the employee's reporting manager, and the chain is sourced from the project Google Sheet | Reflects how approvals actually work here | `leave/approvals.py`, `LEAVE_APPROVER_SHEET_*` |
| D-12 | The desktop companion (BevyLoop) lives in its own repository | It ships on its own cadence and is not a Django app | — |

## Platform

| # | Decision | Why | Where |
|---|---|---|---|
| D-20 | Exactly one process runs background jobs (`manage.py run_scheduler`), and jobs register declaratively | Per-process `BackgroundScheduler()` ran payroll generation and backups up to 8 times per interval, unlocked | `horilla/scheduling.py`, [`compliance/scheduled-jobs.md`](compliance/scheduled-jobs.md) |
| D-21 | The scheduler service stays at one replica | The jobs are not all idempotent; a second copy is a second payslip run | `docker-compose.yml` |
| D-22 | The API is versioned at `/api/v1/`, with `/api/` kept as a deprecated alias rather than redirected | Existing clients already use `/api/`; removing it is the breaking change versioning was meant to prevent | `horilla_api/apps.py` |
| D-23 | `/health/` reports `product` and `api` but **not** the release string | The route is unauthenticated, and advisories name exact versions — handing one over turns a scan into a list of applicable CVEs | `horilla/urls.py::health_check` |
| D-24 | `/ready/` reports scheduler status but does not fail on it unless `HORILLA_REQUIRE_SCHEDULER=1` | A 503 there can pull web out of the load balancer over a delayed job | `horilla/urls.py::readiness_check` |
| D-25 | `HorillaModel.save()` calls `clean_fields()`, not `full_clean()` | The XSS check must run on every write, including DRF and direct `.save()`; but code written while validation was off relies on saves `full_clean()` would reject | `horilla/models.py` |
| D-26 | The API authenticates through `TenantScopedJWTAuthentication`, which sets the company context itself | Middleware runs before DRF resolves the token, so `CompanyMiddleware` leaves API queries unscoped | `horilla_api/authentication.py` |
| D-27 | `rest_framework_simplejwt.token_blacklist` is installed and rotation blacklists | Without it a refresh token survives logout for its full lifetime and every superseded token stays usable | `horilla/settings/base.py` |
| D-28 | Authenticated endpoints are throttled, not just login-failure-locked | `django-axes` counts failures only; valid-credential hammering and authenticated abuse went uncapped | `REST_FRAMEWORK` throttle rates |

## Engineering practice

| # | Decision | Why | Where |
|---|---|---|---|
| D-40 | Line endings are normalised to LF in the object store | Without it a 13-line fix in `leave/forms.py` produced a 2,636-line diff, and a 5,058-line phantom diff on every fork sync | `.gitattributes` |
| D-41 | The `ruff` rule set is scoped to defects the codebase already passes, with the remaining findings recorded as a backlog | The full `E,F,B` set reports ~4,500 findings; a gate that fails on 4,500 gets disabled, which is worse than no gate | `pyproject.toml` |
| D-42 | The coverage floor is the honest branch-coverage number, ratcheted up only | The floor was 5 while real coverage was far above it — a gate that cannot fail reads as one | `Makefile`, `.coveragerc` |
| D-43 | `gitleaks` scans only what a push adds, not full history | 161 findings across 21,741 commits, dominated by a vendored bundle and a committed dump, and history is immutable — nobody could pass it | `.github/workflows/quality.yml` |
| D-44 | `pip-audit` ignores `PYSEC-2026-2860` (pdfkit) **by ID**, not by disabling the gate | No upstream fix exists; it is mitigated in `base.methods.generate_pdf`. By ID, a new vulnerable pin still fails the build | same |
| D-45 | Tests run on PostgreSQL, not SQLite | A SQLite-only suite never exercises the transaction semantics, `JSONField` lookups, constraint deferral or migration DDL we ship on | `.github/workflows/unit-tests.yml` |
| D-46 | Bevy behaviour goes in a Bevy app or a named extension point, not scattered through upstream files | Every in-place edit is a future merge conflict, worst during a security update | [`compliance/keep-the-fork-mergeable.md`](compliance/keep-the-fork-mergeable.md), `horilla/inherit/` |
| D-47 | `CLAUDE.md` is a one-line `@AGENTS.md` import, not a symlink | A symlink makes Cursor inject the copy twice | `CLAUDE.md` |
| D-48 | The People Operations suite is served as static files to signed-in staging users, with fictional data and an explicit allowlist | HR needed to review it without it being wired to real records | [`reference/PEOPLE_OPERATIONS.md`](reference/PEOPLE_OPERATIONS.md) |
