## Payroll v4 · 12 November 2026

Payroll sync now starts with fixed-cycle/custom/30-day period selection, eligibility preview, separate Late unpaid totals, all-employee frozen runs and payroll-ready summary CSV. CSV import is the working recommended path; automatic Google sheet creation/linking is explicitly a production connection blueprint. See docs/PAYROLL_RUNBOOK.md (or PAYROLL_RUNBOOK.md from this docs directory) for formulas and operation. This supersedes older single-batch-only sync instructions below.

# Current v3 update — 11 November 2026

HR / Super Admin validation only. No colleague approval layer. 28 fictional scenarios plus zero-expense test mode. Payroll runbook, shared asset hashes and current test results are authoritative. The following older notes are retained as implementation history and are superseded where they describe manager routing.

# Developer and PM handoff

## Intended outcome

Employees submit eligible business expenses with minimal input. One assigned HR/Manager reviewer decides each claim. HR groups approved unpaid reimbursements into an exact payout batch. Payroll receives only that batch's locked CAD reimbursement. A paid expense never becomes eligible again merely because the month or salary date changed.

## What the prototype implements

The executable engine validates positive two-decimal amounts, required receipt/invoice/purpose, known categories/currencies, subscription periods and personal payment. Duplicate vendor/invoice pairs and employee/vendor/billing-period combinations are blocked across active and paid claims. Reused filenames, similar claims, over-limit claims, missing prior approval and Other are review flags. HR may explicitly resolve policy flags in a decision reason. Coverage, limits and routing are illustrative admin settings, not agreed Bevy policy.

Approvals require a reason, an authorized demo role and a reviewer different from the claimant. Approved amounts cannot exceed the claim. Edits to unreleased claims return them to review. Released and paid claims are locked in the UI. A batch selects only approved, unreserved claims before its cutoff. The demo filters by incurred date (day precision), so late submitted older expenses remain eligible. It locks per-line rates, rounded CAD and exact claim IDs. Sync uses `(Batch ID, Claim ID)` upserts. Payment confirmation requires a synced batch, actual date and reference. Uncertain transfers are held until manually reconciled. Failed batches keep reservations; cancellation removes the simulated active export and releases claims. Paid history remains excluded.

## Production data model

Use a transactional database, fixed-precision decimal amounts and immutable identifiers.

- Employee: ID, work email, manager ID; no base salary.
- Expense: ID, owner ID, category, incurred date, submitted timestamp, amount/currency, vendor/service, plan, billing period, invoice, purpose, payment source, private evidence key and hash, revision, status.
- Review: claim/revision, reviewer ID, decision, approved original amount, policy snapshot, resolved flags, reason and timestamp.
- Policy: coverage, service allowance, cap currency/amount, period, prior approval, receipt rules, effective dates and routing/delegate IDs. Never let employees pick their approver.
- FX quote: provider, base/quote currency, rate, provider as-of, retrieved time, expiry and optional HR override reason/actor. Use decimal arithmetic. CAD/CAD is 1.
- Payout batch: ID, employee, scheduled date, cutoff timestamp and timezone, immutable version, state, release actor/time and payment confirmation reference/date. Never store total salary transfer.
- Allocation: batch/claim IDs, approved original amount, locked rate/quote ID, payable CAD cents and allocation status. Add a database constraint allowing at most one active full-claim allocation per expense.
- Sync outbox: batch/version, idempotency key, expected line count/total, attempts, remote row keys and reconciliation result.
- Append-only audit: actor, event, record version, previous/new values, reason and timestamp.

## Enforce on the server

Role switches in this demo are for presentation. Production endpoints must check authenticated identity and record ownership on every read/write. Employee sees their own evidence and requests specifically assigned to them for review. A manager uses that same Employee portal and Approval inbox; there is no Manager role/view. HR manages expense operations; Super Admin oversees configuration. Review rights come from the stored reviewer Employee ID, never from a client-supplied role label. No self-approval, including delegated and HR claims: route these to another authorized reviewer. Never trust client IDs, amounts, flags or locked rates.

Validate real dates, supported currency codes/minor units, amount bounds, file size/type and billing-period structure. Normalize vendors/services and invoice identifiers carefully. Hash receipt bytes and compare across historical imports; filenames are not sufficient. Flag OCR/amount mismatches, cross-employee similarities, unusual spending and unsupported services. Suspicious is a flag for review, not an automatic fraud accusation.

Shared receipts require an explicit split group, original receipt total and currency, approved allocations, reason and audit. Enforce combined allocations <= receipt total. The prototype blocks repeat invoices conservatively; this shared-receipt exception remains a production task. Import expense-only historical claims before launch for meaningful duplicate detection.

Use object storage with private signed downloads, malware scanning, retention policy, encryption and access logs. Never place receipts or real employee data in GitHub.

## Payout transaction and retries

1. HR previews eligible approved unpaid claims. Late claims are included based on unpaid state, not last-paid-date exclusion.
2. At release, validate latest claim versions and policy limits, obtain a fresh shared quote or explicitly approved override, then atomically reserve claim IDs and freeze their CAD lines. The demo combines prepare/release; production may add a separate preview.
3. Round each CAD payable line to two decimals; sum those same cents for the batch total. Recheck policy limits using a recorded FX snapshot and require review of material differences.
4. Commit the batch and an outbox event in one transaction. Prevent concurrent batch assignment with constraints/row locks. Repeated HTTP requests reuse an idempotency key and return the original result.
5. Sheet worker upserts the same batch/version/claim keys, verifies count/total, then marks the sync reconciled. Partial API failures retry the same frozen snapshot. Sheets alone is not the source of truth or a transactional payment ledger.
6. Confirm only the actual reimbursed claim IDs after a successful transfer is verified. Scheduled date, sync success and salary dispatch alone do not imply payment.
7. A failed transfer remains unpaid/reserved. An uncertain transfer cannot be retried until reconciled. Paid confirmation is idempotent. Cancellation requires verified not-paid status; production exports are voided with history instead of silently deleted.
8. Additional approved claims after release go into a supplementary batch. Paid/released corrections use linked adjustments; never rewrite a confirmed payment. Full-claim reimbursement first; future partial payments require allocations and a remaining balance.

## Google Sheets boundary

Create a dedicated expense export spreadsheet. Grant the portal's service identity access only to that file. The salary workbook's owner imports selected batch CAD totals by stable Employee ID. The portal must have no permission to the salary workbook. Hidden/protected tabs do not create this boundary.

Ledger columns: Batch ID, version, Claim ID, Employee ID, category, incurred date, original amount/currency, approved original amount, locked rate, quote source/as-of, CAD payable, approval reference, sync state, payment state/reference/date and void status. Keep a per-batch employee summary. Import only the selected non-void batch total; do not sum historical exports into every new payroll.

The demo's local ledger/CSV demonstrates the mapping and retry behavior; connecting a real sheet requires server credentials, outbox implementation and tested reconciliation. Do not implement a browser-to-salary-workbook connection.

## FX behavior

Maintain a server-side provider adapter and cache one timestamped snapshot for all views. Refresh on a configured schedule and distinguish provider quote time from retrieval time. Show original plus estimated CAD until release. Show locked payable CAD after release and in exports/history. A rate failure must never silently use an invented rate. Allow saving the original claim, but hold release if stale/missing unless HR confirms an override with a reason and source label.

Receipt amounts never change with FX. Fees and execution-rate differences require separate approved adjustments. The daily public endpoint in the demo is optional and not an execution-rate guarantee; select a provider and staleness policy before production.

## Acceptance and verification

Run `node --test tests/engine.test.cjs`. The tests cover invalid inputs, duplicates, unsupported spending, role/self-approval, over-approval, reservations, late claims, cutoffs, FX locking, rounding, sync failures/retries, cancellation, payment confirmation and uncertain transfers. The browser Proof lab executes 14 core scenarios on independent seed states.

Production acceptance also needs simultaneous-request transaction tests; cross-user evidence/record authorization tests; receipt upload and scanning checks; real Sheets partial-failure/retry tests; provider outage/stale-rate handling; policy revision races; backup/restore and audit retention; accessible mobile verification; and real payout reconciliation against the chosen payment process. Passing prototype tests does not prove these external systems.

## Version 2 requirements supersede the earlier single-review prototype

Every claim now requires HR final approval, after a selected manager's decision. Manager approval creates Awaiting HR, never Approved. Store separate manager and HR records; HR amount cannot exceed the manager amount, and one actor cannot complete both layers. Resubmission invalidates earlier approvals. New claims require actual attachment metadata and the browser adapter persists blobs, validates headers/size and computes SHA-256. Category validators enforce selected meal dates, subscription cycle/service dates, trip dates, item quantity and course details. See INTEGRATION.md for reusable package boundaries and the host handoff. The earlier filename-only / single-approval descriptions are historical and no longer describe the current demo.

Production APIs must verify upload ownership and object existence, scan files, reserve claims and commit approval transitions atomically, reject stale versions and protect reviewer eligibility. A PDF signature check is not a malware scan; SHA-256 is exact-file matching, not semantic invoice fraud detection. Optional invoice references are not invented by the app. A server must retain immutable receipt versions and approvals and must not accept browser-provided hashes as authoritative. The role picker/host bridge remains demo plumbing.

## Single-date claims and shared approval inbox — 11 November 2026

Every employee has an Approval inbox. Any active colleague may be selected for initial review; HR receives every submission immediately and gives the final decision after that review. No selection goes directly to HR. Self-approval, repeated decisions and the same actor completing both stages are blocked. Employees submit only for their signed-in identity; there is no Expenses account picker.

One expense date is required; no start/end inputs. Category-specific fields remain minimal. Bills are mandatory. Duplicate claim IDs, receipt hashes, invoice references, same-day meals and overlapping subscription coverage are checked, including paid history. Similar spending and policy exceptions need human review.

HR/Super Admin → Payroll sync shows an expense-only mapping, frozen payload preview, selected-batch CSV exports, failure/retry simulation and reconciliation. Mismatched row counts, keys, identity or amounts block payment confirmation. Retries repair the same batch; each paid claim gets one settlement allocation.

The reimbursement subledger balances Approved CAD + locked FX adjustment = Paid CAD + Outstanding CAD. Original-currency balances remain separate. Employees do not enter debit/credit journal lines. This is a reimbursement ledger, not a full accounting system.

Google Sheets remains clearly labelled simulated. Production requires an authenticated server connector, database transactions/unique constraints, receipt storage/scanning and append-only audit records. Give it access only to an expense-only spreadsheet. The salary workbook owner imports only the selected Batch ID and Employee ID reimbursement total; base salaries never enter this portal. Browser tests do not prove production isolation or concurrency safety.
