# Environments and deploy

## The three environments

| Environment | URL | Branch | Database |
|---|---|---|---|
| Local | http://localhost:8000 | your branch | `make dev`'s `db` service |
| Staging — the live internal portal | https://hr-portal.bevy.dev | `staging` | v2, compose project `horilla-v2` |
| Production | separate host | the `1.0` line | v1, **not yet migrated** |

"Staging" is a misleading name: it is the HR portal people actually use. A broken `staging` is a
broken portal, and there is no CI in front of it.

## Branches

| Branch | What it is |
|---|---|
| `staging` | **Where work lands.** Cut from it, PR into it. Deploys on push |
| `1.0` / `master` | The v1 line, still production |
| `bevy-hr-portal-dev-2.0` | The branch the server checkout was built from during the v2 cutover |
| `2.0`, `dev/v2.0` | Upstream Horilla's branches. Not ours; see [upstream-merge](../playbooks/upstream-merge.md) |

`CONTRIBUTING.md` and `.github/PULL_REQUEST_TEMPLATE.md` describe PRs to the **open-source** project
(`dev/v2.0`, `[ADD] APP:` commit tags). They do not apply to work here —
[`AGENTS.md` — Defaults](../../AGENTS.md#defaults) does.

## The PR number you open is not the PR number you get

The `bevy-automate` bot **closes every new PR and reopens it under the next number**, leaving a
comment on the original: `PR closed and reopened in #<M>`. Observed on #19→#20, #21→#22 and
#23→#24.

So after `gh pr create`:

```powershell
gh pr view <n> --repo bevycommerce/bevy-horilla --comments
```

Read the bot's comment for the new number, and work against that PR from then on — reviews,
comments and labels on the closed one go nowhere. Anything you set at create time (labels,
reviewers, assignees) may not carry over, so re-apply it on the reopened PR.

## How a deploy happens

1. A PR merges into `staging`.
2. `.github/workflows/staging-deploy.yml` fires on the push and runs on the self-hosted runner
   (`[self-hosted, horilla-staging]`), with `concurrency: deploy-staging` so two deploys cannot
   overlap.
3. Its only step is `sudo -n /usr/local/sbin/horilla-staging-deploy`.
4. That script fast-forwards the server checkout, refuses a dirty tree, refuses a Postgres published
   on `0.0.0.0:5432`, and rebuilds the `horilla-v2` compose project.
5. The container entrypoint applies migrations and runs `collectstatic` **before** gunicorn binds.
   On a large migration set that is minutes of downtime.

The runner connects **outbound** to GitHub. Inbound SSH from GitHub is not used.

`.env` and `docker-compose.staging.yml` live on the server and are not in the repository.

## What this means for you

- **A merge into `staging` is a deploy.** Click-test before merging, not after.
- A migration in the PR is a migration that runs on the portal during the next deploy. Say in the PR
  what it does to existing rows and roughly how long it takes.
- Nothing else deploys. There is no manual deploy step, no separate release branch and no staging
  "promote" button.
- Do not SSH to the box, and do not change the deploy script or the workflow as part of another
  change ([`compliance/protected-paths.md`](../compliance/protected-paths.md)).

## Staging today

Recorded in [`../v1-to-v2.md`](../v1-to-v2.md), checked 24 Nov 2026 — re-verify before relying on
it:

- The v2 app runs from the server checkout as compose project `horilla-v2`, database `horilla_db` in
  container `horilla-v2-db-1`, volume `horilla-v2_postgres_data`.
- The v1 database container still exists on `127.0.0.1:5432` with the v1 app container stopped.
- The v1 archive and the copy script are under `/root/v2-cutover/`.
- The data copy is done: 76 users, 75 employees, 658 attendance rows, 185 leave requests, 73
  contracts, 1,370 candidates. Passwords still sign in. History and audit stayed in the v1 database.
- The box has **2 GB of RAM** and cannot run a second app beside staging. That is also why
  [bounded data access](../compliance/bounded-data-access.md) is a hard rule here.

Attendance, Workspace (sign-in, breaks, Fix My Times), Daily Updates and Reminders are the v2 apps.
People Operations is served at `/people-ops/`, `/hr/`, `/expenses/` and `/insurance/`;
`/daily-updates/` is the real app, not the prototype.

## Production has not moved

Production is still v1. The migration procedure, including what must **not** be done, is
[`../v1-to-v2.md`](../v1-to-v2.md). The constraints that matter even if you never run it:

- Do not point a staging runner or a staging `.env` at production.
- Do not migrate a v1 database in place.
- Do not run `make wipe`, `make restore` or `make backup`.
- Do not publish Postgres or Redis, and do not commit passwords or dumps.

## Health and observability

| Endpoint | Purpose |
|---|---|
| `/health/` | Liveness. Cheap, no dependency checks; used by the Docker healthcheck. Reports `product` and `api` version, deliberately **not** the release string — that would turn a scan into a list of applicable advisories |
| `/ready/` | Readiness. Checks the database, Redis when `REDIS_URL` is set, and reports scheduler status. Does not fail on scheduler unless `HORILLA_REQUIRE_SCHEDULER=1` |
| `/metrics/` | Prometheus scrape for the job runner. Staff-only, and nginx denies it from outside |

`ALLOWED_HOSTS` must include `localhost`, because the image healthcheck calls
`http://localhost:8000/health/`.

Keep `SECURE_SSL_REDIRECT=0` where TLS terminates at the proxy.

## Services

`docker-compose.yml` (dev) and the prod overlay define: `web` (gunicorn), `scheduler`
(`manage.py run_scheduler`), `db` (PostgreSQL 16), `redis`, `nginx`, and the `staticfiles`, `media`,
`postgres_data`, `redis_data` volumes.

**The scheduler stays at exactly one replica.** The jobs are not all idempotent, so a second copy
means a second payslip run and a second backup. Scaling `web` is safe; scaling `scheduler` is not —
the comment in `docker-compose.yml` says so, and
[`compliance/scheduled-jobs.md`](../compliance/scheduled-jobs.md) is why.
