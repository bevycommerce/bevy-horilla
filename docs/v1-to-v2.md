# v1 to v2

Staging is already serving Horilla v2 at https://hr-portal.bevy.dev. The database copy is done. This branch makes `staging` that same v2 app, plus People Operations, so the next HR pull request deploys from `staging`.

Production has not moved. Do not point the staging runner or the staging `.env` at production.

## What staging runs

Checked 24 Nov 2026.

| Piece | Now |
| --- | --- |
| Code on the server | `/root/bevy-horilla-v2`, `bevy-hr-portal-dev-2.0` at `c704ac30b` |
| v2 database | `horilla-v2-db-1`, database `horilla_db`, volume `horilla-v2_postgres_data` |
| v1 database | container `postgres`, volume `bevy-horilla_horilla-data`, still on `127.0.0.1:5432`. The v1 app container is stopped. |
| Archive | `/root/v2-cutover/horilla-v1.dump` and `/root/v2-cutover/media-v1` |
| Copy script | `/root/v2-cutover/copy_v1_to_v2.py` |

Attendance, Workspace (sign-in, breaks, Fix My Times), Daily Updates, and Reminders are the v2 apps. People Operations is added from the old staging line at `/people-ops/`, `/hr/`, `/expenses/`, and `/insurance/`. `/daily-updates/` stays the real Daily Updates app. The suite page links there.

Copied rows: 76 users, 75 employees, 658 attendance, 185 leave requests, 73 contracts, 1,370 candidates. Six candidates with a null stage were given a stage. Passwords still sign in. History and audit stayed in the v1 database.

## After this branch is merged to origin/staging

The installed script still builds `bevy-hr-portal-dev-2.0`. Change `/usr/local/sbin/horilla-staging-deploy` only after `origin/staging` is this tree. Until then a push would rebuild the old v1 checkout and take the site down.

The script should fast-forward `/root/bevy-horilla-v2` to `staging`, refuse a dirty tree, refuse Postgres published on `0.0.0.0:5432`, and rebuild project `horilla-v2`. It must not start the v1 app. `.env` and `docker-compose.staging.yml` stay on the server.

## Production

Use another machine, or a maintenance window. This box has 2 GB of RAM and cannot run a second app beside staging.

1. Restore a fresh production dump as a read-only source. Keep that volume.
2. Start an empty v2 database and let the entrypoint migrate before copying.
3. Run `/root/v2-cutover/copy_v1_to_v2.py` from a one-off container that can see both databases. Do not attach the running web container to the source network. Both compose files name the database service `db`.
4. The script keeps primary keys, sends `auth_user` to `horilla_auth_horillauser`, and remaps groups by name. It does not copy history, audit, sessions, or permission rows by id.
5. Set `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` to the production name. Keep `SECURE_SSL_REDIRECT=0` if TLS ends at the proxy. Include `localhost` in `ALLOWED_HOSTS` because the image health check calls `http://localhost:8000/health/`.
6. Compare the same counts, then sign in and open an employee, an attendance page, a leave request, Daily Updates, and People Operations.

Do not migrate a v1 database in place. Do not run `make wipe`, `make restore`, or `make backup`. Do not publish Postgres or Redis, and do not commit passwords or dumps.
