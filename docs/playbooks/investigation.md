# Investigation

## Goal

Answer the question. Write no production code.

**Done when:** the question is answered with evidence, or the time box is spent and you say what is
still unknown.

## Before

- Read [`AGENTS.md`](../../AGENTS.md) — *How to read the docs*.
- **Restate the question in one sentence** and agree the time box. Without one, an investigation
  becomes an unreviewed refactor.
- Find the owning app in [`reference/APP_MAP.md`](../reference/APP_MAP.md).
- Check [`DECISIONS.md`](../DECISIONS.md) and [`FOLLOW_UPS.md`](../FOLLOW_UPS.md) — the answer may
  already be recorded, including "we decided not to".

## During

Where to look, in order:

1. **The comment next to the code.** This codebase records *why* inline. `horilla/models.py`,
   `horilla/scheduling.py`, `horilla/settings/base.py`, `pyproject.toml`, `.gitattributes`,
   `.coveragerc` and the CI workflows each explain their own constraint.
2. **`git log -p --follow <file>`** and `git log --oneline -S '<string>'` to find when a line arrived
   and what it came with. Commit messages on `staging` are descriptive sentences.
3. **The URL path.** A route you cannot find in `horilla/urls.py` is appended from an
   `<app>/apps.py::ready()`.
4. **The decorator stack** on the view, and `horilla/decorators.py`, for an access question.
5. **The manager** on the model, for a "why can they see this" question —
   `HorillaCompanyManager` or a plain `Manager`.
6. **`<app>/scheduler.py`** and `/metrics/`, for a "why did this run / not run" question.
7. **Local reproduction** with query logging, for a performance question. Count queries at 10 rows
   and at 500.

Rules while investigating:

- Read-only. No edits to application code, settings, migrations or CI.
- A throwaway script goes in the session scratchpad, never in the working tree.
- Do not run anything against a server or a production database
  ([`compliance/secrets-and-server-access.md`](../compliance/secrets-and-server-access.md)).
- Quote file and line as evidence. "It seems to" is not a finding.
- Say when you are guessing.

## After

- Report: the answer, the evidence (file:line, commit, query count, log line), and what you could
  not determine.
- If it is a defect, hand over to [bug-fix.md](bug-fix.md) with the root cause stated — do not
  start fixing inside the investigation.
- Record what is durable: a decision in [`DECISIONS.md`](../DECISIONS.md), an open question in
  [`FOLLOW_UPS.md`](../FOLLOW_UPS.md), how the subsystem works in its
  [`reference/`](../reference/README.md) file.
- If a doc sent you somewhere and the answer was not there, log it in
  [`navigation/MISSES.md`](../navigation/MISSES.md). That is the main way these docs improve.
