# Smart Employee Workspace - Progress

Last updated: 2026-11-10 (Asia/Dhaka)

## Phase status

| Phase | Status |
|---|---|
| 0 Safety and preparation | Complete (2026-11-10) |
| 1 Workspace attendance | Implemented and tested in the cloud test environment; NOT yet run in the owner's Docker (migrations pending there) |
| 2 Daily Updates | Core rules, company feed and Today board implemented and tested; web pages (editor, dashboard, sidebar) not built yet |
| 3 Reminder engine | Groundwork only (adapter is_day_off, notify) |
| 4 Desktop API | Attendance endpoints done and tested; updates/reminders endpoints not yet |
| 5 Windows Desktop Companion | Not started |
| 6 macOS compatibility | Not started |
| 7 Full QA and documentation | Not started |

## Done in Phase 0

- Confirmed local base commit `bba4b37` and that the git index matches it exactly (no local commits, no staged changes).
- Verified attendance sign in/out, validation, payroll, overtime, work record and correction code paths (see plan section 2).
- Verified scheduler setup (single `run_scheduler` process, DjangoJobStore, max_instances=1).
- Verified JWT API and existing clock-in/out endpoints.
- Verified time zone setting in effect (`Asia/Kolkata`, no `.env`).
- Electron vs Tauri evaluated against current documentation; Electron selected (plan D13).
- Wrote WORKSPACE_IMPLEMENTATION_PLAN.md and this file.

## Files changed in the project so far

- Added: `WORKSPACE_IMPLEMENTATION_PLAN.md`, `WORKSPACE_PROGRESS.md` (documentation only)
- No existing file has been modified. No migrations. No database changes. Nothing installed.
- Local-only: `.git/info/exclude` entries; `.env` with `TIME_ZONE=Asia/Dhaka` (created by the Phase 0 script).

## Tests run

- Phase 0 baseline: 2450 tests, 1 failure + 2 errors, all pre-existing and unrelated (see WORKSPACE_TEST_REPORT.md).

## Storage migration (completed 2026-11-10)

- Active project location is now `D:\HR-Portal\horilla-hr`. The folder name stays `horilla-hr` so the Docker Compose project name and volume names are unchanged. The old copy at `C:\Users\WAHID\Desktop\horilla-hr` is no longer used; never start Docker Compose from it.
- Docker Desktop disk image moved through Docker Desktop settings to `D:\DockerData`.
- Fresh database backup (custom format, plain SQL, media): `D:\HR-Portal-Backups\20261110-143559`. The old `backup.sql` (6 Nov) lacks all custom tables and must not be relied on.
- Verified after the move: identical row counts, all custom migrations applied, website healthy, identical git change list (49 entries).
- Migration scripts and reports: `D:\HR Portal\migration-tools`.
- Hibernation turned off by the owner to free space on C:.

## Owner decisions

- 2026-11-10: the local database contains test data only. Company time zone is `Asia/Dhaka`. Switch `TIME_ZONE` to `Asia/Dhaka` through configuration, with no conversion of existing rows.

## Blockers

- The command-line environment on the PC works, but it has no Docker access. Docker steps run through PowerShell scripts the owner starts (`D:\HR Portal\migration-tools`).

## Session log 2026-11-10 (evening)

Development and testing now happen in Claude's cloud copy of the repo (PostgreSQL 16, Python 3.12, same requirements), synced to `D:\HR-Portal\horilla-hr` through git bundles. Claude's shell on the PC has no Docker, so anything that must run in Docker is done through owner-run PowerShell scripts.

Commits on `feature/smart-workspace` (newest last):
- `c36b46d31` D7: break/Away logic moved to `attendance/services/breaks.py` (views unchanged in behaviour; 11 tests; full attendance suite 304 OK)
- `c125e3b46` workspace_attendance core: adapter, services, audit log, idempotency, migration 0001 (33 tests)
- `aac371b54` Workspace API `/api/workspace/v1/` (status, sign-in, sign-out, break, away, corrections; 12 tests). Bug fixed: employee row lock must use the base manager with FOR UPDATE OF self.
- `896c3eec3` daily_updates core + migration 0001 (22 tests)
- `3cbb8d707` company feed and Today board, privacy test (5 tests)
- `61b0867e9` My Workspace card on both homepages + Fix My Times page (23 tests, built by Sonnet subagent, reviewed)
- `99100ae13` reminder groundwork in adapter (not used yet)

Test totals in the cloud environment: Workspace suite 106 OK; attendance + payroll 1295 OK.

New migrations to apply in Docker: `workspace_attendance 0001`, `daily_updates 0001` (only new tables; no existing table changes).

Known limitations so far:
- Not yet clicked through in a real browser; layout, dark mode and mobile untested.
- "Write Today's Update" button on the card is a placeholder until the Daily Updates pages exist.

## Exact next task (resume here)

1. Apply the 2 new migrations in Docker on the PC (owner script), restart, run the Workspace tests inside the container, then look at the card in the browser.
2. Phase 2 web pages: Daily Updates editor (Midday / Skip / Combined / EOD, copy unfinished items, edit with history) and the company dashboard (Today / Attendance / Work Updates / History, filters, visibility notice), top-level sidebar item. Hook the card's "Write Today's Update" button to it.
3. Phase 3: workspace_reminders app (ReminderDelivery unique per employee/day/kind/attempt, ReminderSnooze, one APScheduler job every 2 min, pending actions, notifications).
4. Phase 4 rest: updates, skip, reminders, snooze endpoints + docs/workspace_api.md.
5. Phase 5: Electron desktop companion (Windows first).
