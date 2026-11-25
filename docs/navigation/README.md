# Navigation misses

When a doc sends you somewhere and the answer is not there, that is a **miss**, and it is the most
useful thing you can report about this doc set. Log it in [`MISSES.md`](MISSES.md).

A miss is not a complaint. It is the only signal that tells us which docs are lying, which router
rows point at the wrong file, and which subsystem has no home yet.

## What counts as a miss

- A playbook or router row sent you to a file that did not answer the question.
- [`reference/APP_MAP.md`](../reference/APP_MAP.md) pointed at the wrong app.
- A doc described behaviour the code no longer has.
- You needed something and there was no doc for it at all — you had to read the code from scratch.
- A link was broken, or an anchor did not exist.

What is **not** a miss: the docs said "read the code" and you did; or you did not open the doc the
router pointed at.

## How to log one

Add a row to [`MISSES.md`](MISSES.md):

```markdown
| 2026-11-25 | docs/reference/APP_MAP.md | Where leave approvals live | Said `leave`; the Bevy chain is in `leave/approvals.py`, not named | open |
```

Keep it to one line. If the same miss has a row already, add a tally mark to it rather than a new
row — frequency is what decides what gets fixed first.

## How a miss gets closed

If the fix is a line, make it in the PR you are already working on and mark the row `fixed`. If it
is a whole missing doc, leave the row open and add it to
[`FOLLOW_UPS.md`](../FOLLOW_UPS.md) so it is tracked rather than forgotten.
