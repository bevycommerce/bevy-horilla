# Upstream merge

## Goal

Bring Horilla upstream changes into `staging` without losing Bevy behaviour or breaking the portal.

**Done when:** the merge is clean, Bevy features still work, migrations are consistent, and the
After checklist is complete.

This is the highest-risk routine change in the repository. It is never a side effect of another
task.

## Before

- Read [`AGENTS.md`](../../AGENTS.md) and
  [`compliance/keep-the-fork-mergeable.md`](../compliance/keep-the-fork-mergeable.md).
- **Know what is ours.** The Bevy surface is: `workspace_attendance`, `daily_updates`,
  `workspace_reminders`, `expense`, the leave-approver chain (`leave/approvals.py`,
  `leave/models.py::LeaveApprover`), the attendance break additions, the Bevy entries in
  `horilla/settings/base.py` and `horilla/urls.py`, `horilla/people_operations_preview.py`,
  `prototypes/`, and `.github/workflows/staging-deploy.yml`. Confirm the current list with
  `git diff` against the upstream merge base rather than trusting this paragraph.
- Read upstream's release notes and `CHANGELOG.md` for the range. Note any Django version bump,
  settings restructure, or model change in `attendance/`, `payroll/`, `leave/` or `horilla_auth/`.
- Add the upstream remote if it is missing, and fetch without merging:

  ```powershell
  git remote add upstream https://github.com/horilla/horilla-hr.git
  git fetch upstream
  ```

- Do this on a branch off `staging`, never on `staging` itself.
- **Say in chat** which upstream ref you are merging, what the range contains, and what you expect to
  conflict. Wait for approval.

## During

- Merge **the ref that was approved in Before**, with renormalisation — `.gitattributes` normalises
  line endings, and a branch created before that landed conflicts on *every line* of any file whose
  endings changed:

  ```powershell
  git merge -Xrenormalize <approved-ref>    # e.g. upstream/2.0, or a release tag
  ```

  Merging a different ref than the one approved can leave the requested changes absent while every
  check still passes, so confirm `git log --oneline HEAD..<approved-ref>` is the range you described
  before merging.

  A conflict that survives that is a genuine content conflict. `git diff --ignore-cr-at-eol` shows
  the real difference when a diff looks far larger than the change.
- Resolve conflicts by **keeping upstream's version and re-applying ours on top** wherever ours is an
  addition (a settings entry, a URL entry, a sidebar item). Do not hand-merge two versions of an
  upstream function line by line.
- A conflict inside an upstream file that exists only because Bevy edited it in place is a signal:
  move that edit to an extension point in `horilla/inherit/` as part of this merge, and note it.
- **Migrations:** after resolving, run `python manage.py makemigrations --check --dry-run`. If
  upstream and a Bevy app both added migrations, check the dependency graph —
  `python manage.py showmigrations` and `python manage.py migrate --plan` on a scratch database.
  Never delete or renumber an upstream migration.
- **Requirements:** take upstream's `requirements.txt` and re-add any Bevy pin, then re-run
  `pip install -r requirements.txt` and `pip-audit --requirement requirements.txt`.
- Do not take the opportunity to tidy anything.

## After

- Full gate, not the short one: `ruff check .`, `black --check` and `isort --check-only` on the
  settings paths, `python manage.py check`, `check --tag horilla.tenancy`,
  `makemigrations --check --dry-run`, and `make test-smoke`.
- Migrate a scratch database from empty, then migrate a copy of a realistic database, and record how
  long it took. The staging boot runs `migrate` before the web server binds.
- `make dev` and click-test, in this order:
  1. sign in; 2. Workspace card — sign in, break, sign out; 3. Fix My Times; 4. Daily Updates
  submission; 5. a reminder delivery; 6. an expense; 7. a leave request through the Bevy approver
  chain; 8. an employee profile; 9. an attendance list and validation; 10. a payslip; 11. the
  People Operations pages at `/people-ops/`; 12. `/health/`, `/ready/`, `/api/v1/swagger/`.
- Check the scheduler container starts and `/metrics/` reports jobs.
- Say in the PR: the upstream range, every conflict and how it was resolved, the migration plan, what
  you click-tested, and what you did not.
- Record anything upstream changed that we deliberately did not take, in
  [`DECISIONS.md`](../DECISIONS.md).
- Merge the PR and watch the staging deploy. A failed deploy here takes the portal down, so do it
  when someone is around.
