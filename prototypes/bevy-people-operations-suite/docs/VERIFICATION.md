# Verification — 23 November 2026

Local verification used Node 24.22.3 and Django 4.2.24 (matching company requirements for the preview test). All executed checks passed.

| Check | Result |
| --- | --- |
| HR portal | 33 tests passed |
| Expenses | 133 tests passed, including three-month fictional payroll replay |
| Insurance | 17 tests passed |
| Daily Updates logic | 13 tests passed |
| Suite HTTP routes | 5 tests passed |
| Review regression tests | 9 tests passed |
| Django authenticated preview | 5 tests passed |
| Total named automated tests | **215 passed; zero failures** |
| Optional isolated PostgreSQL checks | Fresh schema, own-only manager RLS, stale exception reviews, wall-clock handover, late leave correction, legacy field preservation and actual v5→v6 upgrade passed |
| Protected Worker build / syntax / shared expense copy | Passed |
| Public handoff scan / whitespace checks | Passed |

Reproduction and complete console output: [verification-output.txt](verification-output.txt). Node dependencies were installed from the committed lockfile with lifecycle scripts disabled. The Windows npm command path is exercised with a simulated Windows process; a native Windows machine was not used.

## Reproduce

From this prototype folder run `npm ci --ignore-scripts`, `node scripts/check-public-handoff.mjs`, and `npm run verify`. For Django use the company Python environment and `python tests/test_django_preview.py`; the test uses minimal isolated settings, no company database and no real accounts.

SQL files are deliberately excluded from the company repository. Set `BEVY_DAILY_SQL_DIR` to the reviewed private fixture directory, including schema_v5_reference.sql, then run `npm run test:database`. The logged optional database check used that separate directory. Without it the standard verify command explicitly reports SKIP for the optional database check; CI must not describe a skipped check as passed. Company production migrations require a separate Django implementation.

## Tested review risks

Regression coverage includes name reuse with a new employee ID, missing legacy ownership/reapproval, claim identity in frozen exports, stale payroll previews, incomplete FX quotes, asynchronous upload versus reservation, stale open editors, focused Daily Updates drafts and current-employee session binding. Payroll instructions reject duplicate current rows, conflicting duplicate imports and wildcard email criteria; real Google Sheets acceptance still belongs to the staging reviewer.

Insurance tests require valid insurer/bank milestones before completed amounts, redact rejected server responses, and validate chronological durations. The local review uses fictional records only. Current period presets recalculate on refresh while custom dates and pagination remain intact.

## Remaining release checks

Local checks do not replace the exact commit's GitHub CI result, signed-in company staging acceptance, external-account denial, production load/concurrency testing or an approved real Google connection. No bank transfer, live Sheet write, deployment, merge, server SSH or company database migration was performed. The prototype's browser-local account selectors are demonstrations, not server authorization for real employee data.
