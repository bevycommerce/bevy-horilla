# Code review

## Goal

Catch what would reach the HR portal. `staging` has no CI, so this review is the gate.

**Done when:** every changed file has been read against the checks below, and findings are reported
Blocker / Major first.

## Before

- Get the diff: `git diff staging...HEAD` for the current branch, `git diff staging...<branch>` for
  another, or `gh pr diff <n>` for a PR.
- **Put the revision under review on disk before running the gate.** `gh pr diff` and
  `git diff <branch>` only display a revision; they do not change the checkout. Reviewing one
  revision while the gate tests another reports a pass for code it never ran — use
  `gh pr checkout <n>` or `git switch <branch>` first (note the branch you started on, and do not
  switch with a dirty tree). If you cannot switch, review from the diff and say in the report that
  the gate did not run against the target.
- Read [`AGENTS.md`](../../AGENTS.md) — hard rules. Open the compliance rule for each area the diff
  touches.
- Run the gate before reading the code — `/hr-check`, or
  [`AGENTS.md` — Checks](../../AGENTS.md#checks). A failing `makemigrations --check` is a Blocker and
  needs no further review to report.

## Blockers

Report these first; they stop the merge.

- A model change with no committed migration, or an edit to a migration already applied on staging.
- A secret, dump, `.env`, `media/` file or password in the diff.
- A missing or weakened server-side permission check, or a gate that exists only in a template — a
  new list or detail screen over employee data with `login_required` but no view permission is this.
- A company-scoped model read through `.objects` where the result reaches a user.
- An attendance or payroll change that alters validated rows, the global validation rule, or
  overtime approval ([`workspace-attendance-integrity`](../compliance/workspace-attendance-integrity.md)).
- A `BackgroundScheduler()` or a job started outside `register_job`.
- An unbounded read on a request path: a query inside a loop over employees, or an unpaginated list.
- A change to a [protected path](../compliance/protected-paths.md) that the task did not name.
- A gate loosened to make something pass: coverage floor, ruff rules, settings gate, secret scan.

## Per changed file

| Check | Looking for |
|---|---|
| **Correctness** | Does it do what the PR says? Off-by-one on dates, time-zone assumptions (`TIME_ZONE` defaults to `Asia/Kolkata`), `None` paths, half-day and night-shift cases |
| **Access** | The decorator on the view; a **view permission** on a list or detail screen and not just `login_required` (the generics do not gate the read); the screen mirroring it; the fragment route guarded by `hx_request_required` |
| **Scoping** | `HorillaCompanyManager` on new models; per-request scoping in a filter's `queryset_fn` |
| **Migration** | Present, readable, reversible if it moves data, named meaningfully, unformatted |
| **Queries** | `select_related` / `prefetch_related` on rendered relations; no ORM call in a loop; aggregation in SQL; pagination intact |
| **Screens** | Generic CBVs, not hand-rolled pages; permission-dependent attributes set in `__init__`, not the class body; `form_valid` returning `self.HttpResponse()` |
| **Forms and filters** | Subclassing `base.forms` / `HorillaFilterSet`; large FK fields behind `ajax_fields` |
| **i18n** | `gettext_lazy` on every user-visible string, including `verbose_name` and messages |
| **Models** | `HorillaModel`, `<thing>_id` FK naming, `verbose_name` everywhere, no new `xss_exempt_fields` without a reason |
| **API** | Backward compatible for mobile and desktop clients; paginated; authenticated class sets the company context |
| **Fork hygiene** | Bevy logic in a Bevy app or extension point; no reformatting of upstream files; no renames of upstream names |
| **Dead code** | What this change orphaned is gone |
| **Diff hygiene** | No debug prints, commented-out code, stray files, screenshots, or unrelated formatting |
| **Docs** | A decision recorded, a follow-up logged, the reference file updated — in this PR |

## Reporting

- Blocker / Major only unless asked for everything. A list of nits buries the one finding that
  matters.
- Each finding: file and line, what breaks, and the concrete scenario where it breaks. "This could
  be cleaner" is not a finding.
- Verify before reporting. Read the surrounding code and the comment above the line — several
  things in this repository look wrong and are deliberate, and the comment says so.
- Say what you could not check (anything needing a server, real payroll data, or the mobile client),
  and whether the gate ran against the target revision or only against the diff.
- For a GitHub PR, submit the review on the PR. Otherwise report in chat.
- If you switched branches to review, return to the branch you started on.
