## Current review · 11 November 2026

See PORTAL_REVIEW_2026-11-11.md for the full current section map. Expense scope section 12 is implemented as a shared browser-local module: HR / Super Admin validation only; no manager/employee approval. The Build guide, permissions summary and payroll handoff now reflect this. See EXPENSE_MODULE.md and EXPENSE_PAYROLL_RUNBOOK.md. Older dated notes below remain historical; production integrations are still pending.

# Developer handoff

## Goal and boundaries

Customize the current internal portal rather than recreate a full HRMS. This frontend is an approved-scope interaction reference, implemented with vanilla ES modules to minimize setup and make patterns easy to port into the existing portal stack. Confirm the actual backend/framework version before choosing a porting approach. This work has not inspected or modified the production portal or its database.

Current modules: branding, simplified navigation, employee records, HR asset control, archive retention, insurance visibility, speed/usability. Existing leave stays in place. Daily Updates is included now, per the owner’s 5 November follow-up. Only Performance remains future scope.

## Reuse map

- Copy CSS tokens, layout and component patterns; adapt them to the existing template framework.
- Keep pure rules in `web/domain.mjs` as reference and mirror them on the backend, with tests in the backend's language.
- Replace `seed()` and `localStorage` with authenticated API-backed records and server-side audit events.
- Remove role/scenario/reset controls in production. Never trust a browser role or employee ID to authorize a request.
- Serve production employee records only after record-level authorization. Hiding fields in the DOM is insufficient.

## Recommended backend contracts (illustrative, not implemented)

| Capability | Suggested contract | Server responsibility |
| --- | --- | --- |
| Directory | GET employees with bounded search and filters | Active records only; field minimization, pagination |
| Profile | GET/PATCH employee by ID | Role and field-level read/write authorization; validation |
| Experience | Joining date + previous months | Canonical date calculation and non-negative values |
| Confidential details | Separate HR-only endpoint/model fields | Exclude bank/NID/personal data from other responses entirely |
| Device assignment | POST asset assignment | Transaction, unique serial, available state, active recipient |
| Return | POST actual return | Date consistency, condition, assignment history |
| Offboarding | POST archive | Remove from active directory; leave assigned devices outstanding |
| Retention | POST keep / explicit DELETE | At least 30 calendar days; authorization and audited confirmation |
| Insurance dashboard | GET sanitized summary/claims | Tracker adapter; field allowlist; confirmed-bank records only |
| Daily records | Session + update revisions + reports | Trusted clock, transactional pause/resume, ownership checks |

## Suggested data entities

Employee; ConfidentialEmployeeDetails; Asset; AssetAssignmentHistory; OffboardingRecord; RetentionDecision; SanitizedClaimProjection; DailySession; WorkInterval; DailyUpdateRevision; ExceptionDecision; AuditEvent. Reuse existing leave/account/department entities. Do not duplicate employee administration or create Teams integration.

## Current roles and permissions

The owner replaced the old separate management view with Super Admin / HR Admin / Employee. Super Admin controls administrative access and settings; HR Admin shares the administrative workspace but only assigned modules; Employee sees their own workspace. The full role, scope and lifecycle rules are in [ROLE_AND_ACCESS.md](ROLE_AND_ACCESS.md). The `web/permissions.mjs` policy is reference code and must be enforced on the production backend, not trusted from localStorage or the role preview selector.

## Insurance adapter

Single source of truth is the existing insurance tracker, never duplicate manual entry. Keep claim submission in the separate portal. Implement a server-side sanitized projection or an authenticated embed only if embedding and access controls support it.

Completed = settled + confirmed bank receipt + valid bank receipt date; reject invalid date sequences from duration averages and flag data quality to HR. Filter completed records by bank receipt date. Filter rejection counts by recorded start date. Distinguish actual insurer rejection from automatic >30-working-day overdue classification. Never call an overdue claim a confirmed insurer rejection.

Date rules: exclude Friday/Saturday, do not exclude public holidays in this version. Start-exclusive/end-inclusive count makes same-day = 0. Prefer actual submission date when recorded; otherwise HR approval. Show that basis clearly. Stage averages and overall average use valid completed claims in the selected period before rounding. The sample fixtures use HR approval only. Production adapter must supply the appropriate start value and basis per record.

Refresh every 60 seconds only while the page is visible; expose manual refresh, last successful timestamp and stale-data error. The prototype refreshes sample data without a network call and includes HR-accessible failure simulation. A real adapter must catch network/API failures and never advance the successful timestamp on failure.

## Daily Updates — included now

Net = closed/open work intervals excluding breaks; flexible start with 8-hour target, no late penalty, extra time recorded. Target Mid-Day at 4 net hours. Capture missed reason and HR decision without overwriting historical submissions. Capture progress, evidence URL, next step, blocker and support contact for Mid-Day/EOD. EOD normally 30–45 minutes before sign-out; exception must be explicit when updates or hours are missing. Missing update flags are distinct from short hours.

Use portal-approved leave and non-working days when generating required records/reminders. Do not omit approved-leave staff only from a UI count: exclude them from the backend reminder job. Weekly/monthly CSVs must include status, work, breaks, extra time, reasons and revision counts. Backend scheduling, notifications, shared storage, concurrent edits, real leave calendars and tamper-resistant clock are not implemented here.

## Production security work before live HR data

Reuse authenticated portal sessions; enforce backend RBAC and per-record ownership; validate and normalize all input; parameterize database queries; use CSRF protection on cookie-authenticated writes; secure file upload/download authorization; encrypt sensitive data/backups appropriately; restrict secrets to server configuration; record server-side audits; rate-limit writes/auth; review retention/deletion dependencies and approved recovery process; run company security review.

Demo domain access is broad company membership for fictional review content only. It does not map production HR roles. No security mechanism can justify calling this static simulation a production HRMS or guarantee it is bulletproof.

## Detailed audit and administration handoff

See `SCOPE_AUDIT.md` for exact section 3/4 field mapping and all 11 source sections. See `ADMIN_BACKEND_BLUEPRINT.md` for every administrative operation, illustrative API, grants, model and consistency rules. Control centre demonstrates module editing; it does not provide a deployed data API. `web/profile-schema.mjs` is the shared display/edit/QA schema. All requested personal, employment, education/experience and bank fields are accounted for.
