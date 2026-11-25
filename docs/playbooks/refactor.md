# Refactor

## Goal

Change the structure, not the behaviour.

**Done when:** behaviour is demonstrably identical, the diff is only structure, and the After
checklist is complete.

## Before coding

- Read [`AGENTS.md`](../../AGENTS.md) — the hard rules apply in full.
- **Say what behaviour must not change,** and how you will know. If you cannot name a way to tell,
  this is not a refactor yet.
- Find every caller. URL names, template `{% url %}` tags, `reverse()` calls, serializer field
  names, sidebar `redirect` entries and `match_prefixes`, and dotted-path strings in
  `accessibility` entries or `register_job` ids are all references a rename breaks and the type
  checker will not catch. Grep for the name as a **string**, not only as a symbol.
- Check whether the file is upstream's. Restructuring an upstream file costs a future merge conflict
  in that file forever ([`compliance/keep-the-fork-mergeable.md`](../compliance/keep-the-fork-mergeable.md)).
  If it is upstream's, prefer an extension point in `horilla/inherit/`, or leave it alone.
- Check whether the mess is load-bearing: `horilla/models.py`'s narrow `clean_fields()` call,
  `horilla/scheduling.py`'s lazy registration, the `base/scheduler.py` explicit `job_id`s and the
  scoped `ruff` rule set all look like things to tidy and are not. Read the comment.
- **State the scope and the risk in chat. Wait for approval.**

## During coding

- One kind of change per commit: move, then rename, then simplify. A commit that does all three is
  unreviewable.
- Keep public names stable, or change them everywhere in the same commit: URL names, permission
  strings, template paths, serializer fields, model field names, `job_id`s.
- A model field rename is a migration *and* a data migration *and* every template and serializer
  that names it. Usually not worth it.
- No behaviour changes smuggled in — not a fixed bug, not a better default, not an added validation.
  Those are separate PRs.
- Do not reformat files you are not otherwise changing, and never run a formatter over the whole
  repository. `ruff`'s unenabled rule backlog in `pyproject.toml` is deliberate: clearing it is its
  own work, not a side effect.
- Delete what the refactor orphans. That is the point of it.

## After coding

- Run the gate — `/hr-check`, or [`AGENTS.md` — Checks](../../AGENTS.md#checks). Include
  `makemigrations --check --dry-run` even when you believe no model changed; a moved model class
  changes `app_label`.
- Run the tests for every app you touched, not just the one you edited:
  `python manage.py test <app_label> <app_label>`.
- **Click-test the screens that use the moved code**, including the sidebar entry and any HTMX
  fragment route. A broken `reverse()` or swap target only shows at runtime.
- Diff-read the whole change yourself. In a refactor, the review is the diff.
- Say in the PR what moved, what it was called before, and what you verified behaves the same.
