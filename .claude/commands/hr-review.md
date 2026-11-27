---
description: Review the current branch or a PR against this repo's per-file checks; Blocker and Major findings only
argument-hint: "[PR number, branch, or nothing for the current branch]"
---

Review $ARGUMENTS (the current branch against `staging` if nothing was given).

Follow [`docs/playbooks/code-review.md`](../../docs/playbooks/code-review.md) exactly — its Blockers
list and per-changed-file table are the checklist. Do not substitute a generic review.

Steps:

1. **Work out the target, pin it to one commit, and make it the checkout.** The gate in step 2 runs
   against the working **tree**, so reading one revision while testing another reports a passing
   gate for code it never ran.

   Start with `git status --porcelain`. **Refuse a dirty tree on every target, the current branch
   included** — there the diff is of commits while the gate would test your uncommitted edits, so a
   pass can belong to code that is not in the diff and not in the PR. Note the current branch first
   so you can return to it.

   | Argument | Base | Diff | Get the files onto disk |
   |---|---|---|---|
   | nothing | `staging` | `git diff staging...HEAD` | already the checkout |
   | a branch name | `staging` | `git diff staging...<branch>` | `git switch <branch>` |
   | a PR number | its `baseRefName` | `gh pr diff <n>` | `gh pr checkout <n>` |

   For a PR, read the head commit and the base **before** the diff and confirm the checkout landed
   on that commit. The two commands are separate requests, and an author who pushes between them
   leaves you reviewing one revision and testing another:

   ```powershell
   gh pr view <n> --repo bevycommerce/bevy-horilla --json headRefOid,baseRefName
   ```

   ```powershell
   gh pr checkout <n> --repo bevycommerce/bevy-horilla
   ```

   ```powershell
   git rev-parse HEAD
   ```

   If `git rev-parse HEAD` is not the `headRefOid` you read, stop and report the mismatch rather
   than reviewing across two revisions.

   `gh pr diff` and `git diff <branch>` only *display* a revision — neither changes the checkout.
   If you cannot or should not switch (dirty tree, or the user asked you not to), review from the
   diff alone and say explicitly that the gate was **not** run against the target.

2. Run the gate against that checkout, passing the base from the table: `/hr-check <base>`. It
   picks the test labels from `<base>...HEAD`, so the base has to be the one the diff used — a PR
   into `dev/v2.0` compared against `staging` lists changes that already shipped and can miss the
   app the PR actually touches. A failing `makemigrations --check` is a Blocker on its own and needs
   no code reading to report. **CI does not run on `staging`**, so this review is the gate.
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
