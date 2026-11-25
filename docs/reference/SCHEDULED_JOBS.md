# Scheduled jobs

One process runs background work: `manage.py run_scheduler`, the `scheduler` container.
Jobs register with `horilla.scheduling.register_job`, which resolves callables lazily and stores
them in APScheduler's `DjangoJobStore` with `max_instances=1` and `coalesce=True`.

Rule: [`compliance/scheduled-jobs.md`](../compliance/scheduled-jobs.md).
How-to: [`DEVELOPER_GUIDE` — Background jobs](../DEVELOPER_GUIDE.md#background-jobs).

## Current jobs

Read from the `register_job` calls in each `<app>/scheduler.py`. Re-derive rather than trust this
table if the answer matters:

```powershell
Select-String -Path */scheduler.py -Pattern 'register_job'
```

| App | Job | Trigger |
|---|---|---|
| `base` | `rotate_shift`, `rotate_work_type`, `undo_shift`, `switch_shift`, `undo_work_type`, `switch_work_type` | every 4 h (explicit ids `job1`–`job6`) |
| `base` | `recurring_holiday`, `sync_roster_shifts` | every 4 h |
| `base` | `clear_expired_sessions` | cron 03:00 |
| `base` | `trim_scheduler_history` | cron 03:15 |
| `attendance` | `create_work_record` | every 30 min, and cron 00:30 |
| `attendance` | `auto_punch_out` | every 5 min |
| `employee` | `update_experience` | every 4 h |
| `employee` | `block_unblock_disciplinary` | every 60 s |
| `leave` | `leave_reset` | every 4 h |
| `payroll` | `expire_contract` | every 4 h |
| `payroll` | `generate_pay_period_payslips` | every 3 h |
| `recruitment` | `candidate_convert` | every 5 min |
| `recruitment` | `recruitment_close` | hourly |
| `asset` | `notify_expiring_assets`, `mark_expired_assets` | daily |
| `asset` | `notify_expiring_documents` | every 4 h |
| `pms` | `cyclic_feedback_creation` | cron 08:00 |
| `report` | `run_report_subscriptions` | hourly |
| `outlook_auth` | `refresh_outlook_auth_token` | every 50 min |
| `workspace_reminders` | `_run_reminders` | interval from `workspace_reminders/scheduler.py` |
| `workspace_reminders` | `_cleanup_keys` (Workspace idempotency keys) | cron 03:17 |

Several jobs pass `misfire_grace_time` so they still run after a restart window — `create_work_record`
allows 3 h on the interval and 9 h on the nightly cron, `auto_punch_out` 10 min, the 03:00 cron jobs
6 h.

## The one known exception

`horilla_backup/scheduler.py` still creates its own `BackgroundScheduler()`, so it runs one copy per
gunicorn worker. The comment in the file records why: an admin editing the Google Drive backup
config calls start/stop on it from `views.py`, so it needs a mutable live scheduler rather than a
static registry.

The stated fix is to move job control behind the `DjangoJobStore` — `run_scheduler` owns execution,
views only write config rows. Tracked in [`FOLLOW_UPS.md`](../FOLLOW_UPS.md). **Do not use this file
as a precedent for a new job.**

`pg_backup/` also instantiates a scheduler, and is not in `INSTALLED_APPS`.

## Operating

- The scheduler runs as its own compose service (`scheduler` in `docker-compose.yml`), one replica.
  Two replicas would reintroduce duplicate runs.
- `/ready/` reports `scheduler: ok` once `run_scheduler` has written jobs to the jobstore, and
  `missing` if that process has never run. It does **not** fail the probe unless
  `HORILLA_REQUIRE_SCHEDULER=1` — a 503 there can pull web out of the load balancer over a delayed
  job.
- `/metrics/` exposes job counts and failure rates in Prometheus format. Staff-only, and nginx
  additionally denies it from outside.
- `trim_scheduler_history` keeps the `django_apscheduler` execution table from growing without bound.

## Adding a job

```python
# <app>/scheduler.py
from horilla.scheduling import register_job


def expire_stale_swaps():
    ...


register_job(expire_stale_swaps, "interval", hours=4)
```

Then import `scheduler` from the app's `apps.py::ready()` if it is not already (see
`pms/__init__.py` for the import pattern). Add the row to the table above in the same PR.
