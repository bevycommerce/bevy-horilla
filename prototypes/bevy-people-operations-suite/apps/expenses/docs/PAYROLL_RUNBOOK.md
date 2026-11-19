# Payroll handoff v4.1 — 12 November 2026

## Recommended easy workflow
Use a fixed monthly expense cycle. Pay day 10 means previous month 10th through current month 9th (both inclusive). Actual payment can be early/late; it does not reset the period. The 31st clamps to the last day of shorter months. Custom ranges and a 30-day shortcut are available, but rolling 30 days can overlap or leave calendar gaps; exact claim/payment tracking is always required.

1. Once only: Payroll sync → Set up payroll emails once. In the demo paste company emails only (no salaries), or use the clearly fictional portal list. Save. The mapping is retained for later periods; real Google/OAuth remains a production connector.
2. Every period: choose cycle month + usual pay day → Use monthly cycle. Set the planned actual payment date separately. For different employees' pay cycles, prepare separate runs or employee selections.
2. Preview eligible expenses. Review the selected-period claims and separately labelled Late unpaid claims. The Late unpaid checkbox explicitly includes/defers older approved, unpaid expenses. Excluded claims and reasons are expandable.
3. Press Sync expenses for this period. Email matching, exact claim reservation, FX locking and summary upsert are automatic in the demo. A repeated sync for the same From/To + employee scope reuses its existing Run ID; it never appends newly approved claims to an already frozen handoff. Later approvals remain eligible for the next period. Preview details first remains optional.

Prepare the exact claims. One Run ID groups an employee payout batch per employee. Original approvals and CAD rates lock. Multi-employee preparation is atomic.
4. Generate payroll CSV. One row per normalized company email: current-period CAD, late-unpaid CAD, total reimbursement CAD, claim count, READY status. Claim breakdown is a separate CSV. The demo reconciles local export rows before handoff.
5. Import CSV into Expense_Import in the private salary workbook; use Run ID + company email, not names or just a month. Replace a run's existing import rows on retry, never append duplicate copies. Keep previous salary runs in payroll history.
6. Salary workbook alone calculates base salary + reimbursement + approved positive/negative adjustments. No base salary is stored or requested by the portal.
7. After successful transfer, record Run ID + normalized company email in Payroll_History, retain frozen historical payroll values, and confirm the exact portal payout batch with actual date/reference. Sync/export alone never marks Paid.

## What is included
- In-period: HR/Super Admin approved, unpaid, unreserved, personal expense with proof and currently covered category, dated inside From/To and no later than planned transfer/today.
- Late unpaid: same eligibility, dated before From; separately listed and only included when the checkbox is on.
- Excluded: drafts, rejected, needs-information/unapproved, paid, another active payout reservation, company-paid, uncovered/missing proof, later/future expenses. HR flags need documented human review; software cannot guarantee legitimacy.
- Period From/To are payroll controls; employee submission still has just one expense date. Date basis is Asia/Dhaka.

## Examples
A November cycle for pay day 10 is 10 October–9 November. Paying on 7 November includes only eligible claims through 7 November; claims for 8–9 November remain unpaid and can enter the next run as Late unpaid. Paying on 13 November still uses 9 November as the fixed cycle end, unless HR deliberately chooses a custom period. An older claim approved late is not lost. Paid claims cannot enter another run.

## CSV columns
A Run ID | B Company Email | C Employee | D Period From | E Period To | F Period Expenses CAD | G Late Unpaid CAD | H Reimbursement CAD | I Claim Count | J Export Status | K Internal Employee ID.

## Salary workbook formulas
Create Expense_Import with the CSV. Create Payroll_History with completed Run ID in A and normalized company email in B. On the current salary row: A2 Run ID, B2 company email, C2 base salary CAD, D2 expense lookup, E2 approved adjustments, F2 final pay.

D2 (fails safely for duplicates, missing imports and previously processed runs):

```excel
=IF(COUNTIFS(Payroll_History!A:A,A2,Payroll_History!B:B,LOWER(TRIM(B2)))>0,"ALREADY PROCESSED",IF(COUNTIFS(Expense_Import!A:A,A2,Expense_Import!B:B,LOWER(TRIM(B2)),Expense_Import!J:J,"READY")=1,SUMIFS(Expense_Import!H:H,Expense_Import!A:A,A2,Expense_Import!B:B,LOWER(TRIM(B2)),Expense_Import!J:J,"READY"),"CHECK IMPORT"))
```

F2:
```excel
=IF(ISNUMBER(D2),ROUND(C2+D2+E2,2),"CHECK EXPENSES")
```

A run with no expenses has no export row. After checking that there are no eligible claims, HR may explicitly enter zero reimbursement for that employee; a missing row must not silently become zero. After payment, preserve the final payroll values before adding the completed Run ID/company email to Payroll_History; that guard blocks reuse in a new current payroll row. Never record failed/uncertain transfers as completed.

## Optional automatic Google connection
Future production: Connect Google once → Create expense export sheet → create Expense_Ledger, Payroll_Summary, Instructions tabs → persist spreadsheet ID → reuse it on retries. Service permission is expense-only. Salary workbook owner allows an IMPORTRANGE connection into Expense_Import:

```excel
=IMPORTRANGE("EXPENSE_ONLY_SHEET_URL","Payroll_Summary!A:J")
```

Then use the same guarded lookup. Sync upserts summary by Run ID + Employee ID and detail by Run ID + Claim ID; never append blind duplicates. Setup uses a unique workspace key so retry cannot create another sheet. OAuth/server credentials and real Google writes are NOT connected in this prototype. The Create export sheet button simulates schema setup only, without a fake Google URL. CSV generation works.

## Failures and safeguards
Re-download the same run after download failure. A stale preview is rechecked before reserving. Invalid quotes block release. A failed multi-employee sync does not partly advance the run. Uncertain/held payout blocks export. Cancelled unhanded-off payouts disappear from totals. Once CSV handoff is recorded, this demo blocks cancellation to prevent releasing a claim that payroll might still pay. Production needs a payroll void acknowledgement before cancelling an exported run. Paid history and locked CAD never recalculate.

## Production boundary
Browser-local prototype only. Use database transactions/version checks, unique active claim reservations, immutable employee IDs, outbox retries, spreadsheet readback reconciliation, and a unique processed Run ID + Employee ID record in payroll. Keep bank transfer confirmation separate. Google authorization, real payroll calculation and bank transfers are not performed by the demo.

## Email safety and one-time operation
Portal directory sends the company email with immutable Employee ID. Normalize only case and outer whitespace; do not strip dots, plus aliases or guess typos. Portal duplicate/missing/malformed emails and duplicate IDs block reservation. The saved payroll mapping must contain exactly one matching email for every selected employee; otherwise the whole sync is rolled back. No salary amounts are pasted or requested.

Each new run snapshots company email + Employee ID. A later email/ID change on an unpaid frozen run blocks handoff for review. A legacy ID-only run is not silently remapped: finish its existing payroll handoff and payment. Do not create another email run for the same claims. Paid history retains its original identity. New employees or changed payroll addresses require an explicit connection review, not silent alias matching.

Automatic demo summary rows upsert by Run ID + canonical email; internal ID remains column K. The app never silently joins different people by name. Sync reserves claims immediately; reserved/synced/paid claims are not eligible in the next period. They remain in payout history until payment or documented void handling. Once handed off, cancellation is blocked until payroll reconciliation; failed or uncertain money transfers must not be retried as a new payout.

Production: one OAuth setup creates/reuses the expense-only sheet and persists its ID. Read and revalidate the payroll email roster, upsert/reconcile summaries and use a unique consumed Run ID + Employee ID guard in payroll. Scheduled/unattended Google writes are not implemented in this browser-local prototype. Period sync and CSV are interactive; do not represent the demo as a live integration.

## Three-month fictional payroll replay
Payroll sync → Replay 3-month payroll demo. An isolated instance of the real expense engine simulates September, October and November 2026 for three fictional employees. Steps: Email sync → Calculate payroll → Confirm fictional payment → Check next period. The salary roster exists only in this separate example; normal expense exports contain no base salary. Your workspace claims and connection are unchanged. Fixed fixture FX is illustrative, not a historical market rate.

| Month | Reimbursement CAD (all 3) | Final payroll CAD (all 3) | Example |
|---|---:|---:|---|
| September 2026 | 56.01 | 3,596.01 | Transfer on 8th; 9th expense deferred |
| October 2026 | 67.98 | 3,607.98 | Transfer on 12th; deferred + late-approved claims included once |
| November 2026 | 56.01 | 3,596.01 | Transfer on 10th; prior paid claims excluded |

20 unique expense settlements across 3 months. Draft/unapproved, rejected and company-paid examples stay out. Test buttons demonstrate duplicate import, wrong email and already-processed run blocking. Download all 3 months as a clearly labelled fictional payroll CSV with salary, reimbursement, adjustments, final pay and simulated payment references. These are calculated replay examples, not actual Google Sheets or bank activity.
