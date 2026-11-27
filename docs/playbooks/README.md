# Playbooks

Pick the one that matches what you are doing. Every playbook has the same shape:
**Goal → Before → During → After.** Be judgemental: stop when the risk is unclear, and prefer the
smallest correct change.

**Entrypoint:** [`AGENTS.md`](../../AGENTS.md). Open `DEVELOPER_GUIDE.md` and `ARCHITECTURE.md` by
`#` anchor, not whole. Open a compliance rule only when the task touches that area.

| Situation | Playbook |
|---|---|
| New capability, screen or field | [feature.md](feature.md) |
| Something is broken | [bug-fix.md](bug-fix.md) |
| Restructure without behaviour change | [refactor.md](refactor.md) |
| Reviewing or preparing a PR | [code-review.md](code-review.md) |
| Debugging, spike or RCA only | [investigation.md](investigation.md) |
| A whole new Django app | [new-app.md](new-app.md) |
| Merging upstream Horilla in | [upstream-merge.md](upstream-merge.md) |

## Follow, do not rewrite

Opening a playbook means **follow** it. Do not edit `docs/playbooks/*.md` as part of a feature, fix,
refactor or investigation. Task-specific notes stay in chat; what the product now does goes to the
docs the [docs maintenance](#docs-maintenance) section names.

Edit a playbook only when the reusable workflow itself changed. A new playbook file also needs a row
in this table and in [`AGENTS.md`](../../AGENTS.md#start-here-every-task-opens-its-playbook).

## Shared conventions

- **Branch:** cut from `staging`, named `<type>/<short-slug>` — `fix/break-timer-drift`,
  `feat/daily-updates-digest`, `chore/bump-pillow`.
- **PR base:** `staging`. One change per PR.
- **Commit message:** one imperative sentence saying what changed, matching the style on `staging`.
  Upstream's `[ADD] APP: …` tags are for PRs to the open-source project.
- **PR body:** what changed, why, how to click-test it, and whether it adds a migration. No
  screenshots, no extra markdown files in the diff.
- **CI will not check it.** The workflows run on `dev/v2.0` and `2.0`, not `staging` — so run the
  gate yourself ([`AGENTS.md` — Checks](../../AGENTS.md#checks)) or `/hr-check`.
- **After `gh pr create`, find the real PR number.** The `bevy-automate` bot closes the new PR and
  reopens it under the next number, commenting `PR closed and reopened in #<M>` on the original.
  Read that comment and work against `#<M>`
  ([`reference/ENVIRONMENTS.md`](../reference/ENVIRONMENTS.md#the-pr-number-you-open-is-not-the-pr-number-you-get)).
- **Click-test on staging after merge.** A push to `staging` deploys to
  https://hr-portal.bevy.dev within a few minutes.

## Docs maintenance

When a change lands, the knowledge goes somewhere durable in the **same PR**:

| What you learned | Where it goes |
|---|---|
| A product or engineering call worth staying consistent with | [`DECISIONS.md`](../DECISIONS.md) |
| Something still open, deferred or unverified | [`FOLLOW_UPS.md`](../FOLLOW_UPS.md) |
| How a subsystem now works | the matching [`reference/`](../reference/README.md) file |
| A new cross-cutting invariant | a [`compliance/`](../compliance/README.md) rule, via that README's gate |
| A doc sent you to the wrong place | [`navigation/MISSES.md`](../navigation/MISSES.md) |

Nothing goes in a new top-level markdown file. The repository root already carries
`WORKSPACE_IMPLEMENTATION_PLAN.md`, `WORKSPACE_PROGRESS.md`, `WORKSPACE_TEST_REPORT.md` and
`MODULE_INTEGRATION_GUIDE.md` from before these docs existed; they are historical records, not the
place for new material.

## How to invoke

```text
Follow docs/playbooks/<playbook>.md.
<short description, and the issue or ticket if there is one>
Ask before coding.
```

Naming the playbook removes the guess. Keep "Ask before coding" so the agent stops after **Before**
and waits. For an investigation, add a time box.

---

> **Didn't find what you came here for?** Log it in [`../navigation/MISSES.md`](../navigation/MISSES.md).
