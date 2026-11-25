# AGENTS.md — bevy-horilla agent entrypoint

This is Bevy's **internal HR app** (`bevycommerce/bevy-horilla`), a fork of
[horilla/horilla-hr](https://github.com/horilla/horilla-hr) v2 with Bevy-only apps on top. Django
5.2 + PostgreSQL 16 + Redis, ~45 installed apps, server-rendered HTMX screens, a DRF API for the
mobile and desktop clients, and APScheduler for background jobs.

Work lands on **`staging`**, which deploys to **https://hr-portal.bevy.dev**.
`horilla-external` is a different product — leave it alone.

## Start here: every task opens its playbook

1. **Read the matching playbook before planning or editing.** It routes you to the docs that task
   needs. Do not read the whole `docs/` tree.
2. Name it in your first reply (`Playbook: bug-fix`), or `No playbook: <reason>` for a question or a
   one-line tweak. The [hard rules](#hard-rules-compliance) apply either way.
3. **Check [`docs/DECISIONS.md`](docs/DECISIONS.md) and [`docs/FOLLOW_UPS.md`](docs/FOLLOW_UPS.md)**
   for the area you touch. If your plan contradicts a recorded decision, say which one in chat
   before coding. An open follow-up there may be the thing you are fixing, or a trap.

| Task | Playbook |
|------|----------|
| New feature or screen | [feature](docs/playbooks/feature.md) |
| Something broken | [bug-fix](docs/playbooks/bug-fix.md) |
| Restructure, same behaviour | [refactor](docs/playbooks/refactor.md) |
| Review or prepare a PR | [code-review](docs/playbooks/code-review.md) |
| Debug / spike / RCA only | [investigation](docs/playbooks/investigation.md) |
| A whole new Django app | [new-app](docs/playbooks/new-app.md) |
| Pull upstream Horilla changes in | [upstream-merge](docs/playbooks/upstream-merge.md) |

## How to read the docs (token budget)

1. This file, then the playbook. Beyond those, open **only** the section or file you need.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) is the system map (short; links out).
   [`docs/DEVELOPER_GUIDE.md`](docs/DEVELOPER_GUIDE.md) is how to write code here — open it by `#`
   anchor, never whole. A subsystem's detail is in [`docs/reference/`](docs/reference/README.md).
3. **"Which app owns this?"** → [`reference/APP_MAP.md`](docs/reference/APP_MAP.md). Do not grep
   9,000 files to find a feature's home.
4. Much of this codebase explains itself in comments that record *why*. `horilla/settings/base.py`,
   `horilla/scheduling.py`, `horilla/models.py`, `pyproject.toml`, `.gitattributes` and the CI
   workflows each carry the reasoning for their own constraints. Read the comment before changing
   the line.
5. **When a doc sends you somewhere and the answer isn't there**, log it in
   [`docs/navigation/MISSES.md`](docs/navigation/MISSES.md). That list is how these docs get fixed.

## Hard rules (compliance)

Every change, code or docs, follows these. One line each here; the linked doc is the rule. Before
editing an area a rule covers, open that rule.

- [Migrations are committed](docs/compliance/migrations-are-committed.md) — a model change ships its
  generated migration in the same PR; `makemigrations` / `migrate` never run on a server.
- [Protected paths](docs/compliance/protected-paths.md) — infra, settings, auth, permission checks,
  payroll calculation and `.github/` change only when the task names the file.
- [Secrets and server access](docs/compliance/secrets-and-server-access.md) — no `.env`, dumps,
  passwords or keys in the diff; no SSH to a server; never `make restore` / `wipe` / `backup`.
- [Company scoping](docs/compliance/company-scoping.md) — multi-company models read through
  `HorillaCompanyManager`; a raw `.objects` read can cross tenants.
- [Access control](docs/compliance/access-control.md) — the server check comes first and the screen
  mirrors it; use Horilla's decorators, never a template-only gate.
- [Screens go through horilla_views](docs/compliance/screens-use-horilla-views.md) — list, nav, form
  and detail screens subclass the generic CBVs and are driven by HTMX; no bespoke page scaffolding.
- [Workspace attendance integrity](docs/compliance/workspace-attendance-integrity.md) — Horilla owns
  attendance times, events are append-only, every mutating API call is idempotent.
- [Scheduled jobs register centrally](docs/compliance/scheduled-jobs.md) — `register_job` only; a
  local `BackgroundScheduler()` runs once per gunicorn worker.
- [Bounded data access](docs/compliance/bounded-data-access.md) — list and dashboard reads do not
  scale their query count with row count; no query inside a loop over employees.
- [Translatable UI strings](docs/compliance/translatable-ui.md) — user-visible text goes through
  `gettext_lazy`; refresh catalogs with the Makefile target, not a bare `makemessages`.
- [Keep the fork mergeable](docs/compliance/keep-the-fork-mergeable.md) — Bevy behaviour lives in a
  Bevy app or a named extension point, not as scattered edits inside upstream files.

**Enforcement.** Rules bind every edit in a session, not only the first. If a requested change
would break one, **flag it in chat first** (the rule and the Do / Do not line it breaks) and propose
a compliant alternative. Proceed only on an explicit per-change override (`override <rule>,
because …`), restated in chat and in the PR description. Blanket overrides are not valid; "the user
asked for it" is not compliance.

## Defaults

- **PR base:** `staging`. **Branch:** cut from `staging`, named `<type>/<short-slug>`
  (`fix/break-timer-drift`, `feat/daily-updates-digest`).
- **Commits:** one sentence saying what changed, in the imperative — the style already on `staging`
  (`Card: hold back only the automatic refresh while a menu is open`). Upstream's `[ADD] APP: …`
  convention in [`CONTRIBUTING.md`](CONTRIBUTING.md) is for PRs to the open-source project, not here.
- **PR body:** what changed, why, and how to click-test it. One change per PR. No screenshots and no
  extra markdown notes in the diff.
- **CI does not run on `staging`.** Every workflow in `.github/workflows/` triggers on `dev/v2.0`
  and `2.0` only (the one exception is the People Operations prototype job), so a PR into `staging`
  gets no Python gate. **Run the checks yourself** — see [Checks](#checks). This is the most likely
  way a broken change reaches the HR portal.
- **Local dev:** `make dev` (web + scheduler + db + redis), or a venv with `manage.py runserver`.
  Full setup: [`reference/LOCAL_SETUP.md`](docs/reference/LOCAL_SETUP.md).
- **Deploy:** a push to `staging` runs `/usr/local/sbin/horilla-staging-deploy` on the self-hosted
  runner, which rebuilds the `horilla-v2` compose project. Nothing else deploys.
  [`reference/ENVIRONMENTS.md`](docs/reference/ENVIRONMENTS.md).

## Checks

Run these before opening a PR. They are what CI *would* run if it ran on `staging`.

```powershell
ruff check .
black --check horilla/settings horilla/urls.py
isort --check-only --profile black horilla/settings horilla/urls.py
python manage.py check
python manage.py check --fail-level WARNING --tag horilla.tenancy
python manage.py makemigrations --check --dry-run
python manage.py test <app_label>
```

`makemigrations --check --dry-run` is the one that catches a model change merged without its
migration — `migrate` cannot, because it succeeds against whatever is committed.

`make test-smoke` runs the first-party suite and `make test-cov` adds the coverage floor
(`COV_FAIL_UNDER` in the `Makefile` — ratchet it up, never down). Both are slow; run the touched app
labels while iterating. More: [`reference/TESTING.md`](docs/reference/TESTING.md).

Install the formatters once with `pip install pre-commit` then `pre-commit install`, and they run on
every commit.

## Agent skills and commands

[`.claude/commands/`](.claude/commands/) and [`.claude/skills/`](.claude/skills/), which Claude Code
loads automatically:

| Command | What it does |
|---------|--------------|
| `/hr-check` | Runs the gate sequence above and reports only what failed. |
| `/hr-screen` | Adds or changes an HTMX screen, via the `horilla-screen` skill. |
| `/hr-migration` | Generates, reviews and commits a migration safely. |
| `/hr-review` | Reviews the current branch against [`code-review`](docs/playbooks/code-review.md). |

`CLAUDE.md` is a one-line `@AGENTS.md` import, not a symlink, so Cursor and Copilot read the same
router.
