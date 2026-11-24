# v1 to v2 cutover

Staging is on Horilla v2. Production has not been moved. Repeat the steps below against a fresh production copy. Do not point the staging runner or the staging `.env` at production.

The v2 app is `bevy-hr-portal-dev-2.0` (Django 5.2, Python 3.12, user model `horilla_auth.HorillaUser`). Upstream `dev/v2.0` does not have Workspace, Daily Updates, or Reminders. `horilla-external` supplied the copy method. Its importer is recruitment-only and refuses attendance, so it was not run.

## Staging, after the cutover

Checked 24 Nov 2026. Public site: https://hr-portal.bevy.dev/login/ returns 200. `hr.tester` signs in and opens My Dashboard, My Attendances, My Leave Requests, Daily Updates, Fix My Times, and Payslips.

| Piece | Now |
| --- | --- |
| App | `/root/bevy-horilla-v2`, branch `bevy-hr-portal-dev-2.0` at `c704ac30b`. Compose project `horilla-v2`. nginx publishes host `80`. web, Postgres, and Redis are not published. |
| v2 database | container `horilla-v2-db-1`, database `horilla_db`, user `horilla_user`, volume `horilla-v2_postgres_data` |
| v1 database | container `postgres`, database `horilla`, volume `bevy-horilla_horilla-data`, still bound to `127.0.0.1:5432`. The v1 app container `horilla` is stopped. |
| Secrets | `/root/bevy-horilla-v2/.env` mode 600. Keys only: `SECRET_KEY`, `DEBUG=0`, `HORILLA_ENV`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE=America/Toronto`, `SECURE_SSL_REDIRECT=0`, `HORILLA_TRUSTED_PROXIES=nginx`, `DB_INIT_PASSWORD`, `POSTGRES_*`, `DATABASE_URL`, `REDIS_*`, `GUNICORN_WORKERS=2` |
| Archive | `/root/v2-cutover/horilla-v1.dump` (60 MB) and `/root/v2-cutover/media-v1` (704 MB) |
| Deploy | `/usr/local/sbin/horilla-staging-deploy` fast-forwards `bevy-hr-portal-dev-2.0` and rebuilds project `horilla-v2`. A push to the git branch named `staging` runs that script. It does not check out `staging` and it does not start the v1 app. |

The box has 2 GB of RAM. The v1 app and the v2 app cannot run at the same time. The v1 database stays up so the copy can read it.

People Operations (`/people-ops/`) is not in `bevy-hr-portal-dev-2.0`. That route lived only on the v1 staging line.

## Copied rows

| Data | v1 | v2 |
| --- | --- | --- |
| Users | 76 | 76 |
| Employees | 75 | 75 |
| Attendance | 658 | 658 |
| Leave requests | 185 | 185 |
| Contracts | 73 | 73 |
| Candidates | 1,370 | 1,370 |

Checks after the copy: no employee without a user, no attendance, leave, or contract without an employee, no candidate with a missing stage. Six candidates had a null stage. Each was given that recruitment's hired stage, cancelled stage, or otherwise the first stage.

Password hashes were copied with the user ids. Existing passwords still sign in. `bevyadmin` and `hr.tester` both returned 302 to `/`.

History, audit, sessions, and cache stayed in the v1 database (270,212 work-info history rows, 460,689 audit rows, 34,621 sessions). Workspace and Daily Updates rows were not copied. Those tables are empty and the v2 apps create them.

## How the copy works

`docs/v1_to_v2_copy.py` reads the v1 database read-only and writes a v2 database that has already been migrated and has no employees. Primary keys are kept. A column is copied only when both sides have it and the type matches, except integer ids widened to bigint, which Postgres accepts.

- `auth_user` goes to `horilla_auth_horillauser`.
- Groups and permissions are not copied by id. The two v1 groups, `Leave Request Viewer` and `Talent Acquisition Viewer`, are recreated by name. Permissions are attached by `(app_label, codename)`. Members of Talent Acquisition Viewer are also added to the seeded `Recruiter` group.
- New `NOT NULL` booleans and text columns get the model default when v2 left no database default: `cancellation_requested` false, `daily_leave_amount_base` `wage`, `loss_of_pay_is_pretax` true, `daily_leave_amount_divisor` `calendar_days`.
- A jsonb value has to be sent as json. psycopg2 otherwise sends a Python list as a Postgres array and the insert fails.
- An empty v1 table is left empty even if v2 added a required column.
- `recruitment_stage` has a partial unique index, `unique_special_stage_type_per_recruitment`, not a table constraint. v1 has two cancelled stages on one recruitment. The copy drops that index so the stage ids candidates point at can be kept. `DROP CONSTRAINT` does not remove it.

Run the script from a one-off container on both Docker networks. Pass the v1 URL with host `postgres` and rewrite the v2 URL host from `db` to `horilla-v2-db-1`. Do not attach the running web container to the v1 network. Both Compose projects name their database service `db`, and the web container then sends the v2 password to the v1 database.

Tables v1 had and v2 does not: `employee_policy_specific_employees`, `leave_companyleave`, `leave_holiday`, `payroll_overrideattendance`, `project_project_members`, `recruitment_recruitmentsurvey_recruitment_ids`. They were skipped.

## Server setup that differed from the first plan

1. Dump v1 with `pg_dump -Fc` and copy `media/` before stopping anything.
2. Check the v2 code out beside the v1 tree. Do not reuse volume `bevy-horilla_horilla-data`.
3. Stop the v1 app container. Leave its database running. On this box a second app does not fit in memory.
4. Start v2 with `docker-compose.yml`, `docker-compose.prod.yml`, and a server-only `docker-compose.staging.yml`. The extra file clears the dev scheduler password, stops the scheduler from bind-mounting the source tree, and publishes nginx on `80` only at cutover. `ALLOWED_HOSTS` includes `localhost` because the image health check calls `http://localhost:8000/health/`.
5. `SECURE_SSL_REDIRECT` stays `0`. Cloudflare terminates TLS. Redirecting on the origin loops.
6. Wait for `/health/` before copying. The first boot migrates and collects static files and took about 12 minutes.
7. Run the copy. Confirm the counts and the foreign-key checks. Copy `media/` into the v2 media volume and give the files to `appuser` (uid 1000).
8. Sign in on the public URL. Open an employee, an attendance page, a leave request, a contract, and a candidate as an admin. A normal employee is sent back to the dashboard from recruitment, which is permission, not a failed copy.
9. Replace `/usr/local/sbin/horilla-staging-deploy` so the next push cannot start the v1 app. The script is `docs/horilla-staging-deploy.sh`.

`docker-compose.staging.yml` and `.env` stay on the server. They are not in git.

## Production

Use a new machine or a maintenance window. This staging server cannot host a second copy of production beside the live v2 site.

1. Restore a fresh production dump as the read-only source. Keep that volume.
2. Repeat the server setup and the copy against an empty migrated v2 database.
3. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the production name. `TIME_ZONE` stays `America/Toronto` unless production is different.
4. Sign in and compare the same counts: users, employees, attendance, leave, contracts, candidates, plus the six-style null-stage check.
5. Keep the production v1 volume until those pages have been checked. Do not run `make wipe`, `make restore`, or `make backup`.

## Leave these alone

- Volume `bevy-horilla_horilla-data` and the v1 dump.
- In-place `migrate` of a v1 database with the v2 code.
- Copying `django_migrations`, sessions, audit, history, or permission rows by id.
- Publishing Postgres or Redis past localhost.
- Passwords, dumps, and the approver-sheet key in git.
