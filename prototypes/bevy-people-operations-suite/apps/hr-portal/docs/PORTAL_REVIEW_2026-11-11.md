# Portal review — 11 November 2026

All 15 navigation sections were reviewed against the current prototype source and available regression checks. This is a prototype coverage review; it does not certify a connected production backend. Existing layout and workflows are preserved.

| Section | Current behavior / boundary |
|---|---|
| Dashboard | Daily clock, checkpoints, announcements and relevant attention links |
| Daily updates | Login clock, breaks, Mid-Day/EOD, draft/submitted history, corrections and reports; server time/delivery pending |
| My profile | Scope sections 3–4: 24 stored fields, 2 derived experience values, protected confidential view |
| Leave | Vacation 11, Floater 3, unlimited Sick; Jan–Dec, no accrual/carryover, configurable medical threshold |
| Insurance | Fictional confirmed-payment reporting, masked IDs, date/search/pagination and stage metrics; live tracker connector pending |
| Expenses | Shared v3 module, HR/Super Admin only validation, required evidence, duplicate checks, currencies and locked batches |
| Employees | Name/email/filter search, grouped profile editor and permission checks |
| Assets | Exact model/serial, assignment/profile linkage, returns/repairs/history |
| Archived employees | Offboarding, 30-day minimum retention, manual keep/delete/restore, no automatic deletion |
| Performance | Clearly reserved for future confirmed framework |
| Control centre | Module controls, announcements/templates and delegated configuration |
| Access management | Super Admin assigns roles/modules; employee grants never inherit admin powers |
| Portal settings | Super Admin settings; approved policies stay explicit |
| Activity log | Browser-local actor/reason history, production durable audit pending |
| Build guide | Updated to 12 scope sections, one-step expense validation, payroll runbook, test modes, role matrix and current backend boundaries |

## Changes from the previous guide
The guide still said 11 sections and 5 November, omitted section 12 in the coverage table, and described the retired manager approval inbox. These have been corrected. The expense walkthrough and permission matrix now match the shipped module. Other modules were kept in place.

## Reviewer route
Employee → own profile/leave/daily/expenses. HR → assigned modules and expense validation/payout. Super Admin → access/settings and all administrative modules. In Expenses → Controls & tests, use Load 28 fictional scenarios or Start with zero expenses. Payroll sync provides the operator guide; EXPENSE_PAYROLL_RUNBOOK.md covers setup and retry/cancellation/reconciliation.

## Verification
33 regression tests passed; JavaScript syntax checks and protected Worker build passed. All 15 navigation sections were opened in browser QA; each rendered without a visible runtime error. The updated Build guide was inspected for section 12, date, walkthrough and permission matrix. This is a smoke review, not an exhaustive test of every possible action.
