---
description: Review the current branch or a PR against this repo's per-file checks; Blocker and Major findings only
argument-hint: "[PR number, branch, or nothing for the current branch]"
---

Review $ARGUMENTS (the current branch against `staging` if nothing was given).

Follow [`docs/playbooks/code-review.md`](../../docs/playbooks/code-review.md) exactly — its Blockers
list and per-changed-file table are the checklist. Do not substitute a generic review.

Steps:

1. **Work out the target, and make it the checkout.** The gate in step 2 runs against the working
   tree, so reading one revision while testing another reports a passing gate for code it never
   ran. Note the current branch first so you can return to it, and refuse to switch if the tree is
   dirty.

   | Argument | Diff | Get the files onto disk |
   |---|---|---|
   | nothing | `git diff staging...HEAD` | already the checkout |
   | a branch name | `git diff staging...<branch>` | `git switch <branch>` |
   | a PR number | `gh pr diff <n>` | `gh pr checkout <n>` |

   `gh pr diff` and `git diff <branch>` only *display* a revision — neither changes the checkout.
   If you cannot or should not switch (dirty tree, or the user asked you not to), review from the
   diff alone and say explicitly that the gate was **not** run against the target.

2. Run the gate (`/hr-check`) against that checkout. A failing `makemigrations --check` is a Blocker
   on its own and needs no code reading to report. **CI does not run on `staging`**, so this review
   is the gate.
3. Open the compliance rule for each area the diff touches —
   [`docs/compliance/`](../../docs/compliance/README.md). Do not review from memory of the rules.
4. Read every changed file against the per-file table.
5. Verify each finding before reporting it. Read the surrounding code and the comment above the
   line: several things in this repository look wrong and are deliberate, and the comment says why
   (`horilla/models.py`'s `clean_fields()` call, `horilla/scheduling.py`'s lazy registration,
   `base/scheduler.py`'s explicit `job_id`s, the scoped ruff rule set, the coverage floor).

Report Blocker and Major findings only, most severe first. For each: file and line, what breaks, and
the concrete scenario where it breaks. Then say what you could not check — anything needing a
server, real payroll data, or the mobile client — and whether the gate ran against the target
revision or only against the diff.

If you switched branches, return to the branch you started on.

Do not fix anything unless asked.
