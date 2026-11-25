# Documentation

The map of every doc, for people and agents. Agents start at [`AGENTS.md`](../AGENTS.md) and open
only what their task needs.

## Where things are

| Need | Go to |
|---|---|
| I am an agent and I just arrived | [`../AGENTS.md`](../AGENTS.md) — the router |
| What the system is: runtime, request path, URL wiring, the domain map | [`ARCHITECTURE.md`](ARCHITECTURE.md) (short; links out) |
| How to write code here: models, migrations, screens, permissions, scoping, jobs, i18n | [`DEVELOPER_GUIDE.md`](DEVELOPER_GUIDE.md) (open by `#` anchor) |
| **Which app owns this feature?** | [`reference/APP_MAP.md`](reference/APP_MAP.md) |
| Step-by-step workflows: feature, bug fix, refactor, review, investigation, new app, upstream merge | [`playbooks/`](playbooks/README.md) |
| The hard rules every change follows | [`compliance/`](compliance/README.md), summarised in [`AGENTS.md`](../AGENTS.md#hard-rules-compliance) |
| One subsystem's detail | [`reference/`](reference/README.md) |
| Getting it running locally | [`reference/LOCAL_SETUP.md`](reference/LOCAL_SETUP.md) |
| How to test, and what CI does (and does not) check | [`reference/TESTING.md`](reference/TESTING.md) |
| Branches, deploy, what staging is | [`reference/ENVIRONMENTS.md`](reference/ENVIRONMENTS.md) |
| Decisions to stay consistent with | [`DECISIONS.md`](DECISIONS.md) |
| What is still open, deferred or unverified | [`FOLLOW_UPS.md`](FOLLOW_UPS.md) |
| The v1 → v2 cutover and the production procedure | [`v1-to-v2.md`](v1-to-v2.md) |
| The Workspace API contract | [`workspace_api.md`](workspace_api.md) |
| A doc sent me somewhere and the answer wasn't there | [`navigation/MISSES.md`](navigation/MISSES.md) |

## How this set stays useful

1. **One home per fact.** Link to it; do not restate it. A number that changes with the code lives
   next to the code — job intervals in `scheduler.py`, Workspace defaults in `conf.py`, the coverage
   floor in the `Makefile`.
2. **The code often explains itself.** `horilla/settings/base.py`, `horilla/scheduling.py`,
   `horilla/models.py`, `pyproject.toml`, `.gitattributes`, `.coveragerc` and the CI workflows each
   record *why* their constraint exists. A doc that repeats one of those will drift; link to it.
3. **Detail lives next to what it describes.** A subsystem in `reference/`, a rule in `compliance/`,
   a workflow in `playbooks/`. The map and the guide stay short.
4. **Knowledge lands in the same PR as the change.** [`playbooks/README.md` — Docs
   maintenance](playbooks/README.md#docs-maintenance) says where.
5. **Misses get logged and fixed.** When a doc sends someone to the wrong place it goes in
   [`navigation/MISSES.md`](navigation/MISSES.md), and the frequent ones get fixed first.

## Pre-existing documents

These were in the repository before this doc set and are kept as they are:

| File | What it is |
|---|---|
| [`../README.md`](../README.md) | Upstream Horilla's product README and install guide |
| [`../CONTRIBUTING.md`](../CONTRIBUTING.md) | Upstream's contribution guide — targets `dev/v2.0`, **not this fork's workflow** |
| [`../CHANGELOG.md`](../CHANGELOG.md), [`../SECURITY.md`](../SECURITY.md), [`../CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) | Upstream's |
| [`../WORKSPACE_IMPLEMENTATION_PLAN.md`](../WORKSPACE_IMPLEMENTATION_PLAN.md) | The Workspace design record (Nov 2026): the verified baseline and decisions D1–D5. History; current behaviour is in [`reference/WORKSPACE.md`](reference/WORKSPACE.md) |
| [`../WORKSPACE_PROGRESS.md`](../WORKSPACE_PROGRESS.md), [`../WORKSPACE_TEST_REPORT.md`](../WORKSPACE_TEST_REPORT.md) | Point-in-time records of that build |
| [`../MODULE_INTEGRATION_GUIDE.md`](../MODULE_INTEGRATION_GUIDE.md) | How a module integrates with Horilla |

New material goes in this folder, not in a new top-level markdown file.

## Agent entry points

- [`../AGENTS.md`](../AGENTS.md) — the router every agent reads first.
- [`../CLAUDE.md`](../CLAUDE.md) — a one-line `@AGENTS.md` import (not a symlink).
- [`../.claude/commands/`](../.claude/commands/) and [`../.claude/skills/`](../.claude/skills/) —
  `/hr-check`, `/hr-screen`, `/hr-migration`, `/hr-review`.

---

> **Didn't find what you came here for?** Log it in [`navigation/MISSES.md`](navigation/MISSES.md).
