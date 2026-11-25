# Compliance rules

Short Do / Do not invariants that bind **every** change, by an agent or a person. How-tos and
inventories live in [`../DEVELOPER_GUIDE.md`](../DEVELOPER_GUIDE.md) and
[`../reference/`](../reference/README.md).

**Router and one-line summaries:** [`AGENTS.md` — Hard rules](../../AGENTS.md#hard-rules-compliance),
which every agent session loads. Summarise a rule there only; this page is links.

- [migrations-are-committed.md](migrations-are-committed.md)
- [protected-paths.md](protected-paths.md)
- [secrets-and-server-access.md](secrets-and-server-access.md)
- [company-scoping.md](company-scoping.md)
- [access-control.md](access-control.md)
- [screens-use-horilla-views.md](screens-use-horilla-views.md)
- [workspace-attendance-integrity.md](workspace-attendance-integrity.md)
- [scheduled-jobs.md](scheduled-jobs.md)
- [bounded-data-access.md](bounded-data-access.md)
- [translatable-ui.md](translatable-ui.md)
- [keep-the-fork-mergeable.md](keep-the-fork-mergeable.md)

## Enforcement and overrides

Lives in [`AGENTS.md` — Enforcement](../../AGENTS.md#hard-rules-compliance). In short: flag the
conflict in chat before coding, name the rule and the line it breaks, propose a compliant
alternative, and proceed only on an explicit per-change override that is restated in the PR
description.

## Adding a rule

A new rule needs all of:

| # | Criterion | Pass if… |
|---|---|---|
| 1 | **Recurring** | It has been broken more than once, or would be expensive the first time. |
| 2 | **Cross-cutting** | It applies across apps, not to one screen. |
| 3 | **Checkable** | A reviewer can tell from the diff whether it holds. |
| 4 | **Not a how-to** | Guidance belongs in `DEVELOPER_GUIDE.md`; a rule is Do / Do not. |
| 5 | **Stable** | Still true after the next feature. |

A new file also needs a row in this list and a one-line summary in
[`AGENTS.md`](../../AGENTS.md#hard-rules-compliance).

---

> **Didn't find what you came here for?** Log it in [`../navigation/MISSES.md`](../navigation/MISSES.md).
