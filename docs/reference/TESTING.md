# Testing

## Running tests

```powershell
python manage.py test <app_label>              # one app — what you run while iterating
python manage.py test <app_label>.tests.test_x # one module
make test-smoke                                # the first-party suite
make test-cov                                  # the suite under coverage, with the floor
```

Suites live in `<app>/tests/`. `SMOKE_LABELS` in the `Makefile` is the list of app labels the smoke
run covers; `UNIT_LABELS` overrides it.

**Run against PostgreSQL, not SQLite.** CI does, deliberately: a SQLite-only suite never exercises
the transaction semantics, `JSONField` lookups, constraint deferral or migration DDL this app
actually ships on. Set `DATABASE_URL` to a Postgres URL — that also takes the `env.db()` branch in
`settings/base.py`, which avoids the sqlite-only `OPTIONS.timeout` Postgres rejects.

```powershell
$env:DATABASE_URL = "postgres://horilla_user:horilla_pass@localhost:5432/horilla_db"
python manage.py test attendance
```

## The coverage floor

`COV_FAIL_UNDER` in the `Makefile`, currently 26, with branch coverage on (`.coveragerc`). It reads
lower than statement coverage because untaken branches count, which is the more honest number.

The comment in the `Makefile` records the history: the floor was 5 while real coverage was far above
it — a gate that cannot fail is worse than none, because it reads as one. **Ratchet it up as suites
land; never down to make a build pass.**

## The test kit

`horilla/testkit/factories.py` — use these rather than building fixtures by hand:

`make_company`, `make_user`, `make_employee`, `make_attendance`, `make_leave_type`,
`make_leave_request`, `make_available_leave`, `make_payslip`, `make_contract`, `make_job_position`,
`make_recruitment`, `make_stage`, `get_hired_stage`, `make_candidate`, `make_resignation`.

`horilla/testkit/company.py::CompanyFilterTestMixin` — set and clear the company ContextVar that
`HorillaCompanyManager` filters on:

```python
class SwapScopingTests(CompanyFilterTestMixin, TestCase):
    def test_other_company_rows_are_hidden(self):
        self.set_company_context(self.company_a.pk)
        self.assertNotIn(self.row_in_company_b, ShiftSwapRequest.objects.all())
```

Do **not** fake scoping by mutating `model.company_filter` or other class attributes. Current
Horilla tenancy reads `get_selected_company()`, not the class attribute, so such a test proves
nothing. The mixin's `tearDown` clears the context for you.

## What to test

Write a test when the thing would be expensive to get wrong and cheap to assert:

- **A calculation** — worked hours, overtime, leave balance, a payslip component, a proration.
- **An access rule** — the permitted role sees it, the adjacent role does not.
- **A tenancy boundary** — company A cannot read company B's rows.
- **A state transition** — sign in / out, a correction, an approval, a stage move; including the
  impossible transition being a no-op.
- **Idempotency** — a repeated call with the same key returns the stored response and writes nothing
  new.
- **A regression** — a defect that produced a *wrong result*, as opposed to a wrong layout.

Skip a test when a click-test is the better evidence: template rendering, HTMX swap targets, CSS,
sidebar highlighting, PDF layout. Say which you chose and why in the PR.

For a Workspace change that touches an `Attendance` row, the specific test that matters is that a
payslip built from that day counts it exactly as an HR-validated day would
([`WORKSPACE.md`](WORKSPACE.md)).

## Click-testing

Most verification here is still manual, because most of the risk is in screens. Run `make dev`, sign
in as the role that uses the feature, and walk the flow. Then sign in as a role that should **not**
see it.

Cover every surface the change reaches: the HR screen, the employee's own (ESS) view, the mobile API
if a serializer changed, and the export, PDF or email if the field appears there. Say in the PR what
you checked and what you did not.

There is no Playwright or browser-automation suite in this repository.

## The gate before a PR

```powershell
ruff check .
black --check horilla/settings horilla/urls.py
isort --check-only --profile black horilla/settings horilla/urls.py
python manage.py check
python manage.py check --fail-level WARNING --tag horilla.tenancy
python manage.py makemigrations --check --dry-run
python manage.py test <app_label>
```

Or `/hr-check`. **These workflows do not run on `staging`** — they trigger on `dev/v2.0` and `2.0`
only, so this is the whole gate.

`makemigrations --check --dry-run` is the one that catches a model change merged without its
migration. `migrate` cannot (it succeeds against whatever is committed) and `manage.py check`
cannot either.

## What CI checks, where it does run

On `dev/v2.0` and `2.0`:

| Workflow | Checks |
|---|---|
| `Quality` | `ruff check .`; Black/isort on `horilla/settings` and `horilla/urls.py`; `manage.py check` and the tenancy tag; `pip-audit` on `requirements.txt`; `gitleaks` on what the push adds; the production settings gate |
| `Unit Tests` | `makemigrations --check --dry-run`, then `make test-cov` on PostgreSQL 16 |
| `Docker CI` | Image build, migrate, collectstatic, gunicorn start, `/health/` and `/ready/` |
| `CodeQL` | Python static analysis, plus a weekly scheduled run |

On `staging` PRs: only `Bevy People Operations prototype`, and only for changes under
`prototypes/bevy-people-operations-suite/`.

The `gitleaks` job scans only what a push adds. Scanning full history would fail every run forever —
161 findings across 21,741 commits, dominated by a vendored ionicons bundle and a committed SQL dump,
and history is immutable. `pip-audit` ignores `PYSEC-2026-2860` (pdfkit) by ID rather than by
disabling the gate, so a new vulnerable pin still fails the build.
