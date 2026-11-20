## Payroll v4.1 · saved email connection

Set up payroll company emails once; later choose period → Sync expenses. The shared module normalizes email, retains internal Employee ID, blocks identity mismatches and reuses the same run on retry. CSV column B is now Company Email; column K preserves Employee ID. See PAYROLL_RUNBOOK.md for the current guarded formula. Real Google writes are still simulated.

## Payroll v4 · 12 November 2026

Payroll sync now starts with fixed-cycle/custom/30-day period selection, eligibility preview, separate Late unpaid totals, all-employee frozen runs and payroll-ready summary CSV. CSV import is the working recommended path; automatic Google sheet creation/linking is explicitly a production connection blueprint. See docs/PAYROLL_RUNBOOK.md (or PAYROLL_RUNBOOK.md from this docs directory) for formulas and operation. This supersedes older single-batch-only sync instructions below.

# Current v3 update — 11 November 2026

HR / Super Admin validation only. No colleague approval layer. 28 fictional scenarios plus zero-expense test mode. Payroll runbook, shared asset hashes and current test results are authoritative. The following older notes are retained as implementation history and are superseded where they describe manager routing.

# Changelog

## 1.1.0 — 11 November 2026

- Reused the existing Bevy HR portal's exact SVG logo and favicon.
- Matched the portal's green/mint palette, system typography, active navigation, card styling and keyboard focus treatment.
- Added Bevy Commerce metadata, header and footer branding; removed the external font dependency.
- Fixed a validation failure when an unfinished draft lacked vendor/invoice fields.
- Excluded drafts from confirmed duplicate matching while preserving checks against submitted, approved and paid claims.
- Rejected impossible dates and malformed subscription months.
- Rejected fractional-cent approval amounts that could round down to zero.
- Blocked invalid or future-dated FX snapshots before payout reservation.
- Added npm commands, branding guidance and five regression tests. The automated suite now contains 45 passing checks.

## 1.0.0 — 11 November 2026

Expense-only interactive demo with fictional data, role views, review decisions, policy settings, duplicate checks, multi-currency estimates, locked payouts, simulated sheet upserts, CSV export, transfer outcomes and audit history. Initial suite: 40 checks.

## 1.2.0 — 11 November 2026

- Replaced the separate Manager view with Employee, HR and Super Admin views.
- Added optional named manager selection from the demo employee directory.
- Routed each request to that exact employee's Approval inbox with a pending count.
- Kept own expenses separate from assigned approval work; unrelated employees cannot read/review the claim.
- Preserved HR-only category routing, HR fallback, no self-approval and administrator-only payout/ledger screens.
- Migrated existing browser-local generic Manager assignments and added same-origin cross-tab inbox refresh.
- Added 11 routing/access regression tests: 56 automated tests total. Interactive Proof lab now includes 17 scenarios.

## 2.0.0 — 11 November 2026

Mandatory Manager → HR final approval; category-specific forms and snapshots; actual PDF/image bill storage, SHA-256 and previews; meal-day and subscription-service overlap checks; expandable optional fields; new category form reuse; legacy unpaid records held for revalidation; same module integrated into the main HR portal with its employee directory and module grant. Expense tests: 78. HR integration/regression tests: 33.

## Single-date claims and shared approval inbox — 11 November 2026

Every employee has an Approval inbox. Any active colleague may be selected for initial review; HR receives every submission immediately and gives the final decision after that review. No selection goes directly to HR. Self-approval, repeated decisions and the same actor completing both stages are blocked. Employees submit only for their signed-in identity; there is no Expenses account picker.

One expense date is required; no start/end inputs. Category-specific fields remain minimal. Bills are mandatory. Duplicate claim IDs, receipt hashes, invoice references, same-day meals and overlapping subscription coverage are checked, including paid history. Similar spending and policy exceptions need human review.

HR/Super Admin → Payroll sync shows an expense-only mapping, frozen payload preview, selected-batch CSV exports, failure/retry simulation and reconciliation. Mismatched row counts, keys, identity or amounts block payment confirmation. Retries repair the same batch; each paid claim gets one settlement allocation.

The reimbursement subledger balances Approved CAD + locked FX adjustment = Paid CAD + Outstanding CAD. Original-currency balances remain separate. Employees do not enter debit/credit journal lines. This is a reimbursement ledger, not a full accounting system.

Google Sheets remains clearly labelled simulated. Production requires an authenticated server connector, database transactions/unique constraints, receipt storage/scanning and append-only audit records. Give it access only to an expense-only spreadsheet. The salary workbook owner imports only the selected Batch ID and Employee ID reimbursement total; base salaries never enter this portal. Browser tests do not prove production isolation or concurrency safety.

## Three-month fictional payroll replay
Payroll sync → Replay 3-month payroll demo. An isolated instance of the real expense engine simulates September, October and November 2026 for three fictional employees. Steps: Email sync → Calculate payroll → Confirm fictional payment → Check next period. The salary roster exists only in this separate example; normal expense exports contain no base salary. Your workspace claims and connection are unchanged. Fixed fixture FX is illustrative, not a historical market rate.

| Month | Reimbursement CAD (all 3) | Final payroll CAD (all 3) | Example |
|---|---:|---:|---|
| September 2026 | 56.01 | 3,596.01 | Transfer on 8th; 9th expense deferred |
| October 2026 | 67.98 | 3,607.98 | Transfer on 12th; deferred + late-approved claims included once |
| November 2026 | 56.01 | 3,596.01 | Transfer on 10th; prior paid claims excluded |

20 unique expense settlements across 3 months. Draft/unapproved, rejected and company-paid examples stay out. Test buttons demonstrate duplicate import, wrong email and already-processed run blocking. Download all 3 months as a clearly labelled fictional payroll CSV with salary, reimbursement, adjustments, final pay and simulated payment references. These are calculated replay examples, not actual Google Sheets or bank activity.
