---
description: Review the current branch or a PR against this repo's per-file checks; Blocker and Major findings only
argument-hint: "[PR number, branch, or nothing for the current branch]"
---

Review $ARGUMENTS (the current branch against `staging` if nothing was given).

Follow [`docs/playbooks/code-review.md`](../../docs/playbooks/code-review.md) exactly — its Blockers
list and per-changed-file table are the checklist. Do not substitute a generic review.

Steps:

1. Get the diff: `git diff staging...HEAD`, or `gh pr diff <n>` for a PR number.
2. Run the gate first (`/hr-check`). A failing `makemigrations --check` is a Blocker on its own and
   needs no code reading to report. **CI does not run on `staging`**, so this review is the gate.
3. Open the compliance rule for each area the diff touches —
   [`docs/compliance/`](../../docs/compliance/README.md). Do not review from memory of the rules.
4. Read every changed file against the per-file table.
5. Verify each finding before reporting it. Read the surrounding code and the comment above the
   line: several things in this repository look wrong and are deliberate, and the comment says why
   (`horilla/models.py`'s `clean_fields()` call, `horilla/scheduling.py`'s lazy registration,
   `base/scheduler.py`'s explicit `job_id`s, the scoped ruff rule set, the coverage floor).

Report Blocker and Major findings only, most severe first. For each: file and line, what breaks, and
the concrete scenario where it breaks. Then say what you could not check — anything needing a
server, real payroll data, or the mobile client.

Do not fix anything unless asked.
