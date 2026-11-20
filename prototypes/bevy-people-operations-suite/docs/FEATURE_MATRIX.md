# Feature map and delivery status

“Demo” means interactive browser behavior. “Backend source” means code exists and is tested locally, not that the company staging environment has been provisioned.

| Feature | What exists | Remaining before real use | Owner to assign |
| --- | --- | --- | --- |
| Login / employee identity | HR gated hosting adapter; daily optional Supabase Auth | Company SSO, immutable IDs, disable leavers, one role model, server access checks | Backend / platform |
| Profiles | Personal, employment, education, banking schema and edit views; experience calculations | Approved required-field checklist, field-level privacy, database validation and audit | HR + backend |
| Leave | 11 vacation, 3 floater, unlimited sick; Jan–Dec period; no carryover demo logic | Persist balances/requests, transactional overlap rules, timezone/year boundaries; HR confirm medical-document threshold | HR + backend |
| Devices | Assignment/return/correction prototype | Persist unique serial ownership and audit; company inventory integration | HR + backend |
| Insurance | Latest Google source, Sheet contract, count-only rejection response, filters/pagination | Stage with copied Sheet; validate domain access and Google services; deliberately deploy reviewed changes | HR + Google admin |
| Expense submission | Own-claim demo; category, specific expense date, original currency, mandatory proof | Server validation, private uploads, allowed-file/size enforcement and malware scanning, retention | Backend |
| Expense approval | HR and Super Admin only; review and rejection demo | Authoritative roles, approved transitions, self-approval policy, audit trail, concurrent update protection | HR + backend |
| Duplicate / suspicious expense | Duplicate checks and review indicators in demo | Database uniqueness/idempotency; receipt hash + similarity review; category policy; manual suspicious-claim decisions | HR + backend |
| CAD conversion | Original amount/currency and demo conversion calculations | Approved FX provider, rate timestamp, precision/rounding policy; freeze reimbursed rate rather than revalue paid claims | Finance + backend |
| Payroll sync | Period selection, approval eligibility, email matching, export/run ledger and fictional payroll lab | Authorized Google connector or reviewed manual CSV import; durable atomic allocation/payment acknowledgements | Finance + backend |
| Daily timer and updates | Demo; optional SQL-backed sessions, breaks, revisions and exceptions | Company SSO mapping, staging Supabase configuration and browser end-to-end checks | Backend + QA |
| Admin / reports / archive | Role-based prototype screens, exports and documented lifecycle rules | Persist permissions, server audit, authorization tests, retention/deletion policy | Backend + HR |
| Shared portal navigation | HR embeds canonical expenses | Unified navigation/identity and shared persisted state for all modules | Frontend + backend |

## Payroll rule example everyone can follow

An employee normally receives salary on the 10th. Finance chooses a reimbursement cutoff and previews only approved, unpaid, unallocated eligible claims up to that cutoff. If a November claim was already included in a paid run, it must never appear in the December payable total. A late-approved older claim can enter the next open run. Actual transfer date is recorded separately; shifting it by a few days must not silently select a different claim window.

For production, allocate claims to one run in a database transaction. Use unique claim/run constraints and idempotent export/sync requests. Exported is not paid: reserve the run; mark paid only after authorized confirmation. Retries update the same batch rather than creating another payment. Cancel a reserved batch explicitly before reallocation. Do not select “last 30 days” alone, since overlapping windows and late approvals otherwise lose or repeat claims.

The payroll workbook needs only its existing employee email and expense-total column/formula. Keep run identifiers and audit details in the expense ledger/export side, not as required extra payroll columns. Use normalized email + selected payout batch; repeated email rows must be aggregated only for that batch. A linked Sheet may update an **open** run, but a finalized paid run must stay frozen. See the existing [payroll runbook](../apps/expenses/docs/PAYROLL_RUNBOOK.md) for demo operator steps; the durable transactional behavior above remains backend work.
