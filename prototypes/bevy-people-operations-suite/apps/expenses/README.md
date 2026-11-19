## Payroll v4.1 · saved email connection

Set up payroll company emails once; later choose period → Sync expenses. The shared module normalizes email, retains internal Employee ID, blocks identity mismatches and reuses the same run on retry. CSV column B is now Company Email; column K preserves Employee ID. See PAYROLL_RUNBOOK.md for the current guarded formula. Real Google writes are still simulated.

## Payroll v4 · 12 November 2026

Payroll sync now starts with fixed-cycle/custom/30-day period selection, eligibility preview, separate Late unpaid totals, all-employee frozen runs and payroll-ready summary CSV. CSV import is the working recommended path; automatic Google sheet creation/linking is explicitly a production connection blueprint. See docs/PAYROLL_RUNBOOK.md (or PAYROLL_RUNBOOK.md from this docs directory) for formulas and operation. This supersedes older single-batch-only sync instructions below.

# Bevy Commerce · Expense Workspace v3

A Bevy-branded interactive expense-only prototype, also embedded in the Internal HR Portal. Fictional data only; browser-local state.

**Employee → HR / Super Admin validation → expense payout → sheet reconciliation → confirmed reimbursement.** No manager or colleague approvals.


## Simple approval
Employees submit and track only their own claims. Every submission goes directly to HR / Super Admin. Either administrator validates it in one step: approve the full or reduced eligible amount, reject, or request information. No employee/manager reviewer selector, inbox or approval layer. Nobody approves their own claim. Another authorized administrator reviews HR's own submissions. Editing an unreleased claim restarts validation. Released and paid claims stay locked.

## Short form
Required: category, one expense date, vendor/service, amount and original currency, work purpose, and image/PDF bill. Optional invoice/prior approval references are expandable. Subscriptions ask plan and monthly/annual cycle; travel asks destination; purchases ask item/quantity; training asks course. No date ranges. Categories reuse tested form schemas.

## Duplicate and policy checks
Check exact receipt hashes, vendor/invoice references, same employee/day meals and overlapping subscriptions, including paid history. Company-paid and uncovered expenses are blocked. Similar vendor/date/amount, missing prior approval and limits are review flags requiring human judgment. Repeated submission IDs, approvals, batch reservations and payment confirmation do not create extra records. No automated check guarantees fraud detection.

## Currency and payment
Retain original currency and display labelled CAD estimates. Lock rates and per-line rounded CAD when reserving a payout. Only validated unpaid Claim IDs before the cutoff enter it. Salary dates may move: inclusion is tracked by exact batch membership and confirmed payment, not monthly resets. Late older unpaid claims remain eligible. Paid claims never enter a new batch.

A reimbursement subledger balances Approved CAD + locked FX adjustment = Paid CAD + Outstanding CAD. Original-currency balances stay separate. Employees never enter debit/credit journal lines.

## Payroll handoff
HR / Super Admin sees a six-step guide: validate → reserve exact claims → preview frozen payload → sync/export → add selected batch total to separate payroll → confirm actual successful payment. Counts, unique keys, identities and amounts must reconcile. Failure retries reuse the batch. Uncertain transfers are held until checked. The portal handles no base salaries. See PAYROLL_RUNBOOK.md.

## Demo testing
Controls & tests offers 28 fictional scenarios or a clean zero-expense dataset. These replace browser-local expense records only and preserve host employee context. Built-in evidence is clearly fictional. Both sites use identical module assets, verified by hashes. Records do not sync across sites or devices. Google writes and payments are simulated; CSV, attachment handling and state transitions work.

## Run checks
```sh
npm run check
npm test
node scripts/sync-module.cjs /absolute/path/to/hr-checkout
```

The standalone uses dist/. The main HR portal bundles the identical assets behind its company access gate. See docs/PAYROLL_RUNBOOK.md, docs/INTEGRATION.md and docs/test-results.txt.

## Three-month fictional payroll replay
Payroll sync → Replay 3-month payroll demo. An isolated instance of the real expense engine simulates September, October and November 2026 for three fictional employees. Steps: Email sync → Calculate payroll → Confirm fictional payment → Check next period. The salary roster exists only in this separate example; normal expense exports contain no base salary. Your workspace claims and connection are unchanged. Fixed fixture FX is illustrative, not a historical market rate.

| Month | Reimbursement CAD (all 3) | Final payroll CAD (all 3) | Example |
|---|---:|---:|---|
| September 2026 | 56.01 | 3,596.01 | Transfer on 8th; 9th expense deferred |
| October 2026 | 67.98 | 3,607.98 | Transfer on 12th; deferred + late-approved claims included once |
| November 2026 | 56.01 | 3,596.01 | Transfer on 10th; prior paid claims excluded |

20 unique expense settlements across 3 months. Draft/unapproved, rejected and company-paid examples stay out. Test buttons demonstrate duplicate import, wrong email and already-processed run blocking. Download all 3 months as a clearly labelled fictional payroll CSV with salary, reimbursement, adjustments, final pay and simulated payment references. These are calculated replay examples, not actual Google Sheets or bank activity.
