# Follow-ups

What is still open, deferred, or unverified. **Check the rows for the area you are touching** — one
of them may be the thing you are fixing, or the trap you are about to step in.

Add a row when a change leaves something open. Remove it when the change that closes it lands, in
the same PR. Each row names where the evidence is, so it can be re-checked rather than believed.

## Platform

| # | Open item | Why it matters | Where |
|---|---|---|---|
| F-01 | **No CI runs on `staging`.** Every workflow triggers on `dev/v2.0` and `2.0`; the only exception is the People Operations prototype job. A Python change merged into `staging` has no automated gate and deploys straight to the HR portal | This is the single largest quality gap in the repository. Either add `staging` to the triggers, or treat the local gate as mandatory and say so everywhere | `.github/workflows/*.yml`, [`AGENTS.md` — Checks](../AGENTS.md#checks) |
| F-02 | `horilla_backup/scheduler.py` still creates a per-process `BackgroundScheduler()`, so it runs one copy per gunicorn worker | The documented fix: move job control behind the `DjangoJobStore` — `run_scheduler` owns execution, views only write config rows. Until then, Google Drive backups can run up to 8× per interval | the comment in that file, [`reference/SCHEDULED_JOBS.md`](reference/SCHEDULED_JOBS.md) |
| F-03 | Verify the staging deploy script. [`v1-to-v2.md`](v1-to-v2.md) recorded that `/usr/local/sbin/horilla-staging-deploy` still built `bevy-hr-portal-dev-2.0` and was to be switched to `staging` once `origin/staging` was the v2 tree. `origin/staging` now is — confirm the script was switched | If it was not, a push to `staging` rebuilds the old v1 checkout and takes the site down | [`v1-to-v2.md`](v1-to-v2.md), [`reference/ENVIRONMENTS.md`](reference/ENVIRONMENTS.md) |
| F-04 | **Production is still on v1.** The cutover has a written procedure and has not been run | The staging box has 2 GB of RAM and cannot host a second app, so production needs another machine or a maintenance window | [`v1-to-v2.md`](v1-to-v2.md) |
| F-05 | The `/api/` alias is deprecated and should be dropped in a major release | Until it goes, two paths serve the same surface | `horilla_api/apps.py`, [`reference/API.md`](reference/API.md) |
| F-06 | `pdfkit` `PYSEC-2026-2860` has no upstream fix; it is mitigated in `base.methods.generate_pdf` and ignored by ID in `pip-audit` | If pdfkit ever ships a fix, the ignore line is the reminder to take it and drop the mitigation | `.github/workflows/quality.yml` |
| F-07 | `pg_backup/` and `dynamic_fields/` exist in the tree but are not in `INSTALLED_APPS` | Unclear whether they are abandoned or pending. Do not build on them without finding out | `horilla/settings/base.py` |

## Quality

| # | Open item | Why it matters | Where |
|---|---|---|---|
| F-20 | The `ruff` backlog: `F811` (49), `F601` (7), `F402` (5), `E721` (4), `E101` (3), `B035` (3), `B026` (2) are genuine defects still in the tree, then `E722` bare except (148), `B006` mutable default (80), `B904` raise-without-from (71), `F841` (167), `F401` (494), `E712`/`E711` (71), `E501` (1,791), `F403`/`F405` (1,138) | Widen the rule set by clearing these, never by loosening the gate. `E722` and `B904` are the two that hide real failures | `pyproject.toml` |
| F-21 | Branch coverage was 27.6% on 1 Sep 2026 with the floor at 26 | Ratchet the floor up as suites land. Expand `SMOKE_LABELS` / `COV_SOURCE` as apps gain real tests | `Makefile`, `.coveragerc` |
| F-22 | There is no browser-automation suite. All screen verification is manual click-testing | A regression in an HTMX swap target or a permission-gated control is only caught by someone looking | [`reference/TESTING.md`](reference/TESTING.md) |
| F-23 | `.github/PULL_REQUEST_TEMPLATE.md` and `CONTRIBUTING.md` describe PRs to the **upstream** project (base `dev/v2.0`, `[ADD] APP:` commit tags), which is wrong for work in this fork | Anyone following the template targets the wrong branch. `.github/` is a [protected path](compliance/protected-paths.md), so fixing it is its own PR | `.github/PULL_REQUEST_TEMPLATE.md` |

## Docs

| # | Open item | Where |
|---|---|---|
| F-40 | `WORKSPACE_PROGRESS.md` and `WORKSPACE_TEST_REPORT.md` are point-in-time records at the repository root. Once [`reference/WORKSPACE.md`](reference/WORKSPACE.md) covers what they still carry, fold them in and delete them | repository root |
| F-41 | [`reference/SCHEDULED_JOBS.md`](reference/SCHEDULED_JOBS.md)'s job table is hand-maintained and will drift. A `manage.py` command that prints the registry would make it derivable | `horilla/scheduling.py` |
| F-42 | No `docs/operations/` runbooks yet (restoring a backup, rotating a credential, recovering a stuck deploy). The knowledge exists but is not written down | — |
| F-43 | Navigation misses are logged by hand in [`navigation/MISSES.md`](navigation/MISSES.md). Fine at this size; revisit if it gets long | — |
