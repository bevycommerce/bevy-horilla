# Scheduled jobs register centrally

Exactly one process runs background work: `manage.py run_scheduler`, the `scheduler` container.
Jobs declare themselves with `horilla.scheduling.register_job` and are resolved lazily.

The defect this replaced is recorded in `horilla/scheduling.py`: every `<app>/scheduler.py` used to
build its own `BackgroundScheduler()` and `.start()` it at import time, reached from
`AppConfig.ready()`. Import time is once *per process*, and gunicorn runs `cpu*2+1` workers capped
at 8 with `preload_app = False` — so payroll generation, database backups and shift rotation each ran
up to 8 times per interval, with no lock to make the duplicates harmless.

How-to: [`DEVELOPER_GUIDE` — Background jobs](../DEVELOPER_GUIDE.md#background-jobs).
Inventory: [`reference/SCHEDULED_JOBS.md`](../reference/SCHEDULED_JOBS.md).

## Do

- Register in `<app>/scheduler.py`:
  `register_job(my_job, "interval", hours=4)`.
- Let `job_id` default to `<module>.<name>`. It is stable across restarts, so the APScheduler
  jobstore replaces the row instead of accumulating a duplicate on every boot. Pass an explicit
  `job_id` only to keep an existing id (`base/scheduler.py` has `job1`…`job6` for that reason).
- Make the job idempotent. It runs again after every redeploy, and a second run must be a no-op or
  harmless.
- Pass `misfire_grace_time` when the job must still run after a restart window
  (`attendance/scheduler.py::create_work_record` uses three hours).
- Keep the job function importable without side effects: no database access, no thread, no network
  at module import.
- Log what the job did, and at what scale, so `/metrics/` and the logs can explain a slow interval.
- Bound the work. A job that walks every employee reads in batches, like any other
  [bounded data access](bounded-data-access.md).

## Do not

- Instantiate `BackgroundScheduler()`, `BlockingScheduler()` or `.start()` anywhere in app code.
- Start a job from `AppConfig.ready()`, a view, a signal, or a module-level thread.
- Reuse a `job_id` that another job already has. `register_job` raises rather than overwriting,
  because two jobs collapsing into one is silent and worse.
- Make `/ready/` fail on scheduler status by default. `HORILLA_REQUIRE_SCHEDULER` exists for sites
  that want that trade-off; a 503 there can pull web out of the load balancer over a delayed job.
- Add a Celery broker, a cron entry on the host, or a second scheduler process.
