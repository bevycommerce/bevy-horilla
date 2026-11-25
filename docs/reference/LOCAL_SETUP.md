# Local setup

Two ways to run the app. Docker is the fast path; a venv is better for iterating on tests.

Upstream's generic install guide is in [`../../README.md`](../../README.md) and at
docs.horilla.com. This page is what is specific to working on **this** fork.

## Prerequisites

- Python **3.12, 3.13 or 3.14**. Not 3.15 — `spacy` declares `Requires-Python <3.15` and is imported
  at module scope, so the app cannot start.
- Docker Desktop, for the Docker path.
- PostgreSQL 16 and Redis 7, for the venv path.

## Docker (recommended)

```powershell
git clone https://github.com/bevycommerce/bevy-horilla.git
cd bevy-horilla
git checkout staging
make dev
```

That builds and starts four services: `web` (gunicorn on http://localhost:8000), `scheduler`
(`manage.py run_scheduler`), `db` (PostgreSQL 16) and `redis`. The dev stack bind-mounts the source,
so edits are picked up.

**First boot takes about five minutes** — it applies every migration and runs `collectstatic` before
gunicorn binds. The healthcheck's `start_period` is 10 minutes for that reason; a shorter window
makes a fresh start abort as unhealthy. Watch it with `make logs-web`.

Useful targets:

| Command | Does |
|---|---|
| `make dev` | Start the dev stack, building first |
| `make logs` / `make logs-web` | Follow logs |
| `make shell` | A bash shell in the web container |
| `make db-shell` | `psql` into the dev database |
| `make status` / `make restart` / `make stop` | Compose lifecycle |
| `make prod` | The production overlay — requires a real `.env` |

**Never run `make clean`, `make restore`, `make wipe` or `make backup`** against anything you care
about. `make clean` removes volumes. See
[`compliance/secrets-and-server-access.md`](../compliance/secrets-and-server-access.md).

## Virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.dist .env
python manage.py migrate
python manage.py compilemessages
python manage.py collectstatic --noinput
python manage.py runserver
```

In a second terminal:

```powershell
python manage.py run_scheduler
```

**Upgrade pip before installing.** A fresh venv inherits the system pip, and an older one does not
recognise current manylinux wheel tags — it then tries to compile `cryptography` and `PyMuPDF` from
source, which needs a C toolchain most machines do not have.

On Linux or in CI you also need the Weasy/xhtml2pdf system libraries: `libcairo2`, `libpango-1.0-0`,
`libpangocairo-1.0-0`, `libgdk-pixbuf-2.0-0`, `libffi8`, `shared-mime-info`.

## First sign-in

On an empty database the sign-in page shows an **Initialize Database** button. It asks for
`DB_INIT_PASSWORD` from your `.env`, then lets you create the first administrator. There is no
`createsuperuser` step in the normal flow.

`load_data/` holds demo-data JSON fixtures if you want a populated database to click through.

## Environment

`.env.dist` is the template — copy it, never edit the copy into the repository. The variables it
documents: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `TIME_ZONE`,
`SECURE_SSL_REDIRECT`, `DB_INIT_PASSWORD`, `DATABASE_URL`, `POSTGRES_*`, `DB_HOST`, `DB_PORT`,
`REDIS_PASSWORD`, `REDIS_URL`, and the `LEAVE_APPROVER_SHEET_*` trio for Bevy's leave-approver sheet.

Two things to know:

- **`TIME_ZONE` defaults to `Asia/Kolkata`** when nothing sets it, and `USE_TZ = True`. Attendance
  and reminder bugs are often this. Set it explicitly in your `.env`.
- **`horilla/settings/base.py` raises `ImproperlyConfigured`** on insecure production defaults
  (`DEBUG=False` with an insecure `SECRET_KEY`, or `ALLOWED_HOSTS=*`). That is deliberate and CI
  asserts it fires. For local work keep `DEBUG=True`.
- `horilla/settings/local_settings.py` is gitignored and optional. CI stubs it; a missing file is
  fine.

## Formatters and hooks

```powershell
pip install pre-commit
pre-commit install
```

That wires up `ruff --fix`, `black`, `isort --profile black`, YAML checking and whitespace fixing on
commit. `migrations/` and the vendored `notifications/` app are excluded.

## Before you open a PR

Run the gate: `/hr-check`, or the commands in
[`AGENTS.md` — Checks](../../AGENTS.md#checks). **CI does not run on `staging`**, so nothing else
will.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `make dev` hangs then reports unhealthy | First boot migrating; wait, and watch `make logs-web` |
| Pip tries to compile `cryptography` or `PyMuPDF` | `pip` not upgraded inside the venv |
| App will not start on Python 3.15 | `spacy` requires `<3.15` and is imported at module scope |
| `ImproperlyConfigured: production security check failed` | `DEBUG=False` with a default `SECRET_KEY` or `ALLOWED_HOSTS=*` |
| PDF generation fails | Missing Cairo/Pango system libraries |
| Scheduled jobs never fire | `run_scheduler` is not running; `/ready/` reports `scheduler: missing` |
| A whole-file diff on a small change | Line endings — `git add --renormalize .` once, and see [`CONTRIBUTING.md`](../../CONTRIBUTING.md#line-endings) |
| Times off by hours | `TIME_ZONE` unset, defaulting to `Asia/Kolkata` |
