# Protected paths

Some files are load-bearing for the running portal, for who can sign in, or for what people get
paid. They change **only when the task names the file**, and then only by the amount the task needs.

A change here that looks harmless costs a broken deploy, a locked-out workforce, or a wrong payslip
— and `staging` has no CI to catch it
([`AGENTS.md` — Defaults](../../AGENTS.md#defaults)).

## Do not change unless the task names the file

| Path | Why |
|---|---|
| `Dockerfile`, `docker-compose*.yml`, `docker/` | Build, boot order, gunicorn and nginx config; the deploy rebuilds from these |
| `Makefile` | The deploy and test entrypoints, and the coverage floor |
| `horilla/settings/` | Installed apps, middleware order, the production security gate, DRF auth and throttles |
| `horilla/urls.py` | Root routing, the health/readiness/metrics probes |
| `horilla_auth/`, `auth/`, `outlook_auth/`, any `auth_migrations/` | Sign-in, tokens, password handling |
| `scripts/`, `docker/entrypoint.sh` | Boot and operational scripts, wherever they exist on the branch |
| `payroll/methods/` | Payslip calculation |
| `horilla/decorators.py`, `accessibility/` | The permission checks every screen depends on |
| `.github/` | CI and the deploy trigger |
| `.gitattributes`, `.pre-commit-config.yaml`, `pyproject.toml`, `.coveragerc` | The gates themselves |
| `requirements.txt` | A pin change is its own PR, with the CVE or feature reason stated |
| `horilla_theme/static/cdn/**` | Vendored verbatim; reformatting creates a permanent diff against upstream |

## Do

- Treat a needed change to one of these as its own pull request, described on its own terms.
- Read the comment above the line first. Most of these files record *why* the current value is what
  it is — `horilla/settings/base.py`, `horilla/scheduling.py`, `pyproject.toml`, `.gitattributes`
  and the CI workflows all do.
- When a feature seems to need a settings change, check whether an app-level `conf.py` with
  overridable defaults does the job instead (`workspace_attendance/conf.py` is the pattern).
- Say in chat which protected file you need and why, before editing it.

## Do not

- Bundle an infra or settings edit into a feature PR.
- Loosen a gate to make a build pass: the coverage floor, the ruff rule set, the production settings
  check, the secret scan. Widen by cleaning the backlog; `pyproject.toml` and the `Makefile` record
  it.
- Add a dependency to `requirements.txt` as a side effect of a feature.
- Change `horilla/settings/local_settings.py` expectations — it is gitignored and optional, and CI
  stubs it.
