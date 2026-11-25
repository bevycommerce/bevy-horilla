# Bug fix

## Goal

Fix the defect with the smallest blast radius.

**Done when:** the root cause is identified, the fix is focused, the original reproduction passes,
and the After checklist is complete.

## Before coding

- Read [`AGENTS.md`](../../AGENTS.md) — *How to read the docs*, and the hard rules.
- **Reproduce it.** Write down expected versus actual, and which role and company you reproduced it
  as. A bug that only HR sees, or only one company sees, is usually an access or
  [scoping](../compliance/company-scoping.md) bug, not the logic.
- Find the owning app in [`reference/APP_MAP.md`](../reference/APP_MAP.md) and read the code path
  end to end: URL → decorator → view → model → template.
- Check [`DECISIONS.md`](../DECISIONS.md): the behaviour you are about to "fix" may be a recorded
  decision. Check [`FOLLOW_UPS.md`](../FOLLOW_UPS.md): it may already be a known open item.
- Read the comments around the code. This codebase records *why* in comments — `horilla/models.py`,
  `horilla/scheduling.py`, `horilla/settings/base.py` and the CI workflows each explain a constraint
  that looks removable and is not.
- Suspect the usual causes in this app before suspecting the logic:
  - wrong or missing permission decorator, or a template-only gate
  - a model read through `.objects` instead of `HorillaCompanyManager`
  - an HTMX fragment reached without `hx_request_required`, or a swap target that no longer exists
  - a model change merged without its migration (run `makemigrations --check --dry-run`)
  - a job running once per gunicorn worker instead of once
  - attendance validated or not validated by the rule in `attendance/views/views.py`
  - a time-zone assumption: `TIME_ZONE` defaults to `Asia/Kolkata` unless the environment sets it
- If the fix touches attendance or payroll, open
  [`compliance/workspace-attendance-integrity.md`](../compliance/workspace-attendance-integrity.md)
  first and say what it does to already-validated rows and to payslips already generated.
- **State the root cause and the risk in chat. Wait for approval.**

## During coding

- Keep the diff to the defect. No drive-by refactors, no reformatting, no renames — a whitespace
  pass on an upstream file is a future merge conflict
  ([`compliance/keep-the-fork-mergeable.md`](../compliance/keep-the-fork-mergeable.md)).
- Fix the cause, not the symptom. A `try/except` around the error, a `.first()` instead of `.get()`,
  or a default that hides a `None` is a symptom fix — say so explicitly if that is genuinely the
  right call.
- Delete what the fix orphans: the replaced helper, the branch it makes unreachable, the unused
  import. That is part of the fix.
- Preserve backward compatibility for the mobile and desktop clients. An API response shape change
  needs a version note ([`reference/API.md`](../reference/API.md)).
- If the fix needs a data correction on existing rows, that is a reversible data migration, not a
  script someone runs by hand.
- Before editing an area a hard rule covers, open that rule.

## After coding

- Run the gate — `/hr-check`, or [`AGENTS.md` — Checks](../../AGENTS.md#checks).
- **Rerun the original reproduction**, on every surface the fix reaches (HR screen, ESS, mobile API,
  export, PDF, email). Say what you checked and what you did not.
- Add a regression test when the defect was a wrong *result* — a calculation, a balance, a
  permission outcome, a scoping leak. Use `horilla/testkit/factories.py`. A rendering or layout
  defect usually gets a click-test instead; say which and why.
- If the root cause is a recurring cross-cutting invariant, propose a
  [compliance rule](../compliance/README.md#adding-a-rule) rather than fixing only this instance.
- Remove the item from [`FOLLOW_UPS.md`](../FOLLOW_UPS.md) if it closes one; add one if the fix
  leaves something open.
- Self-review against [code-review.md](code-review.md#per-changed-file).
- PR description: the symptom, the root cause, the fix, how to verify, and whether it adds a
  migration.
