---
description: Run the local quality gate (what CI would run if it ran on staging) and report only failures
---

Run the gate for this repository and report **only what failed**, with the command and the relevant
output. If everything passes, say so in one line.

CI does not run on `staging` — the workflows in `.github/workflows/` trigger on `dev/v2.0` and
`2.0` only. This is the whole gate, so do not skip a step because it looks unrelated.

Run these in order, continuing after a failure so the report is complete:

```powershell
ruff check .
black --check horilla/settings horilla/urls.py
isort --check-only --profile black horilla/settings horilla/urls.py
python manage.py check
python manage.py check --fail-level WARNING --tag horilla.tenancy
python manage.py makemigrations --check --dry-run
```

Then run the tests for the apps this branch touched. Work out which from **both** the committed and
the uncommitted changes — a second app edited after the last commit is still about to ship, and a
gate that misses it reports success for code it never ran:

```powershell
git diff --name-only staging...HEAD        # committed on this branch
git status --porcelain --untracked-files=all   # staged, unstaged and new files
```

The first path segment of each result is usually the app label. Take the union, drop paths that are
not app directories (`docs/`, `.claude/`, `.github/`, `static/`, `templates/`, `prototypes/`), and
run what is left in one command:

```powershell
python manage.py test <label> <label>
```

If the union is empty — a docs-only or config-only change — say so rather than reporting that tests
passed.

Do **not** run `make test-smoke` or `make test-cov` unless asked; they take many minutes.

Notes on interpreting results:

- `makemigrations --check --dry-run` failing means a model change has no committed migration. That
  is a blocker — [`docs/compliance/migrations-are-committed.md`](../../docs/compliance/migrations-are-committed.md).
- The tenancy check warning means a model looks company-scoped but reads through a plain manager —
  [`docs/compliance/company-scoping.md`](../../docs/compliance/company-scoping.md).
- `ruff` failing on a rule not in `pyproject.toml`'s enabled list means someone widened the gate;
  check that was intended.
- If `python manage.py check` cannot start, confirm `horilla/settings/local_settings.py` exists or
  is genuinely optional, and that `DJANGO_SETTINGS_MODULE=horilla.settings`.
- Tests need PostgreSQL. If they fail on a SQLite-only error, set `DATABASE_URL` to a Postgres URL
  ([`docs/reference/TESTING.md`](../../docs/reference/TESTING.md)).

Never fix a failure by loosening a gate — the ruff rule set, the coverage floor, the settings gate
and the secret scan each record in a comment why they are where they are.

After reporting, offer to fix what failed. Do not start fixing without being asked.
