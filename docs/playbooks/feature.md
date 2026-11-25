# Feature

## Goal

Ship the smallest change that does what was asked, in the app that owns it, behind the right
permission.

**Done when:** it works on the surfaces people use it on, the migration is committed, the local gate
passes, and the After checklist is complete.

## Before coding

- Read [`AGENTS.md`](../../AGENTS.md) — *How to read the docs*, and the hard rules.
- **Find the owning app** in [`reference/APP_MAP.md`](../reference/APP_MAP.md). A new feature almost
  always belongs in an existing app. A new app needs [new-app.md](new-app.md) and a reason.
- Read the models and the existing screen you are extending. Most Horilla models and settings carry
  comments that record *why*; read them before changing the line.
- Check [`DECISIONS.md`](../DECISIONS.md) and [`FOLLOW_UPS.md`](../FOLLOW_UPS.md) for the area. A
  screen that looks wrong may be a recorded decision; an open follow-up may be a trap.
- Decide the access rule **first**: who may see this, who may change it, and which existing
  permission or role covers it ([`compliance/access-control.md`](../compliance/access-control.md)).
- Decide whether the data is company-scoped
  ([`compliance/company-scoping.md`](../compliance/company-scoping.md)).
- If it is a screen, read [`reference/SCREENS.md`](../reference/SCREENS.md) and the worked example in
  `base/cbv/holidays.py`. Plan which of list / nav / form / detail you need.
- If it touches attendance, open
  [`compliance/workspace-attendance-integrity.md`](../compliance/workspace-attendance-integrity.md)
  before writing anything. Attendance feeds payroll.
- If it touches payroll calculation, stop and say so — `payroll/methods/` is a
  [protected path](../compliance/protected-paths.md).
- **Write the plan in chat**: the app, the models and fields, the routes, the permission, the
  migration, and how it will be click-tested. Wait for approval.

## During coding

- Models extend `HorillaModel`, fields are named and `verbose_name`-d per
  [`DEVELOPER_GUIDE` — Models](../DEVELOPER_GUIDE.md#models).
- Screens subclass the `horilla_views` generics
  ([`compliance/screens-use-horilla-views.md`](../compliance/screens-use-horilla-views.md)). Forms
  subclass `base.forms`. Filters subclass `HorillaFilterSet`.
- Wire routes in `<app>/urls.py` and, for a new app, append them from `apps.py::ready()`.
- Put the permission check on the view, and mirror it in the screen — hide or disable the control
  with its reason.
- Add the sidebar entry in `<app>/sidebar.py`, with an `accessibility` callable if not everyone sees
  it and `match_prefixes` for sibling URLs.
- Every user-visible string goes through `gettext_lazy`
  ([`compliance/translatable-ui.md`](../compliance/translatable-ui.md)).
- Generate the migration as you change the model, not at the end.
- Keep reads bounded ([`compliance/bounded-data-access.md`](../compliance/bounded-data-access.md)):
  no query inside a loop over employees.
- Bevy behaviour goes in a Bevy app or an extension point, not scattered through upstream files
  ([`compliance/keep-the-fork-mergeable.md`](../compliance/keep-the-fork-mergeable.md)).
- Before editing an area a hard rule covers, open that rule. If the request would break one, flag it
  in chat before coding.

## After coding

- Run the gate — `/hr-check`, or the commands in [`AGENTS.md` — Checks](../../AGENTS.md#checks).
  `makemigrations --check --dry-run` must be clean.
- Add a test for the thing that would be expensive to get wrong: a calculation, an access rule, a
  tenancy boundary, a state transition. Use `horilla/testkit/factories.py`. Most small features add
  one test or none; say which, and why.
- **Click-test it** on every surface it reaches: the HR screen, the employee's own view (ESS), the
  mobile API if you touched a serializer, and an export or PDF if the field appears there. Say what
  you checked and what you did not.
- Check the permission from the other side: sign in as a role that should *not* see it.
- Delete what the change orphaned — the replaced helper, the dead branch, the unused import, the
  template nobody renders.
- Record the knowledge: a decision in [`DECISIONS.md`](../DECISIONS.md), anything left open in
  [`FOLLOW_UPS.md`](../FOLLOW_UPS.md), and the subsystem's behaviour in its
  [`reference/`](../reference/README.md) file — in this PR.
- Self-review the diff against the per-file checks in
  [code-review.md](code-review.md#per-changed-file) before opening the PR.
- PR description: what changed, why, how to click-test, and that it adds a migration if it does.
