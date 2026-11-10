# Smart Employee Workspace - Progress

Last updated: 2026-11-10 (Asia/Dhaka)

## Phase status

| Phase | Status |
|---|---|
| 0 Safety and preparation | Complete (2026-11-10) |
| 1 Workspace attendance | Not started |
| 2 Daily Updates | Not started |
| 3 Reminder engine | Not started |
| 4 Desktop API | Not started |
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

## Exact next task (resume here)

1. DONE 2026-11-10: branch `feature/smart-workspace`, checkpoint commit `e38a7e435` (45 files). `.git/info/exclude` keeps backup.sql, *.sql, *.dump, *.backup, .env, seed_candidates.py, setup_leave_test_data.py out of git. Local git identity "Wahid (local)". Nothing pushed. Note: the checkpoint contains an older copy of this progress file; this version supersedes it.
2. DONE 2026-11-10: set `TIME_ZONE=Asia/Dhaka` in a local `.env` file (git-ignored, contains no secrets), restart the containers, and confirm `settings.TIME_ZONE` inside the web and scheduler containers.
3. DONE 2026-11-10: baseline test suite recorded in WORKSPACE_TEST_REPORT.md.
4. Start Phase 1 with D7 (extract break logic into `attendance/services/breaks.py`, tests before and after), then the `workspace_attendance` app.
