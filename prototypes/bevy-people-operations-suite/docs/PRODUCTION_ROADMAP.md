# Implementation plan for the company team

The order below reduces duplicated work. These are proposed next tasks, not claims that production integrations have been delivered.

| Order | Work package | Acceptance condition |
| --- | --- | --- |
| 1 | Agree company staging host, identity and backend conventions | One written deployment/data ownership decision; restricted staging available |
| 2 | Shared employee identity, roles and audit | Immutable employee ID, unique normalized email, inactive-user denial, server authorization on every endpoint; protect bank/profile fields |
| 3 | Persistent HR/expense model and APIs | Validated records in durable database, concurrency/version checks, approved state transitions; browser cannot bypass policy |
| 4 | Receipt storage and policy checks | Private uploads/download authorization, size/type/content checks, malware handling, retention; receipt hashes support duplicate review |
| 5 | Expense ledger, CAD policy and payroll connector | Approved/unpaid-only allocation, decimal monetary calculations, timestamped FX, atomic reservation, retries/idempotency, frozen paid runs |
| 6 | Minimal Google payroll integration | Authorized account connects once; selected open batch exports expenses by email; existing payroll imports only reimbursement total; sync errors visible and safely retryable |
| 7 | Daily updates integration | SSO mappings, correct database migration, server-clock work actions, RLS and cross-user acceptance tests |
| 8 | Insurance staging and portal access | Copied Sheet/project tested; keep Google source of truth; protected navigation/link or reviewed adapter; do not assume cross-origin iframe will work |
| 9 | Operational readiness | Backups/restore, structured audit/logs, alerts, retention, access review and QA sign-off |

## Decisions the PM should capture

- HR confirms mandatory profile fields, sick-leave document threshold, permitted expense categories/limits and who reviews HR's own claims.
- Finance confirms cutoff/timezone, late-approved claims, FX source/rate lock, rounding and payout confirmation ownership.
- Engineering confirms company auth/hosting/database choices, environment access and migration owner.
- Security/data owner confirms insurance backup location, receipt retention and minimum visibility.

Keep these decisions in the company issue/PR with an owner. Do not silently convert an unresolved policy into permanent code. Separate acceptance tests for business rules from deployment checks so reviewers can see exactly which evidence exists.
