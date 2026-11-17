## Current review · 11 November 2026

See PORTAL_REVIEW_2026-11-11.md for the full current section map. Expense scope section 12 is implemented as a shared browser-local module: HR / Super Admin validation only; no manager/employee approval. The Build guide, permissions summary and payroll handoff now reflect this. See EXPENSE_MODULE.md and EXPENSE_PAYROLL_RUNBOOK.md. Older dated notes below remain historical; production integrations are still pending.

# Administration and backend integration blueprint

## What the demo implements

Control centre is an interactive administration UI with browser-local records and validation. The production HR portal's backend has NOT been modified. The existing hosted Worker protects access to fictional demo assets; it is not the HR data API. Port the documented workflows into the existing portal, reusing its accounts, roles, approved leave, database and infrastructure.

## Permissions

Super Admin controls roles, grants, suspension and global portal identity. HR Admin can edit records only in assigned modules. Optional Configuration grant allows module settings only when the corresponding module is also granted. Optional Communications grant permits announcement/template editing. Employee has own-record workspace, no admin edits. Confidential details is a separate grant requiring Employee management. Audit history is read-only; changes append new events. No role preview controls belong in production.

## Suggested operations

All endpoint names are illustrative. No endpoint below is exposed by this prototype. Every write needs authenticated server authorization, record-level access, input normalization, expected revision, actor/reason audit and a transaction where multiple records change.

| Module | UI operation | Illustrative API | Server invariants |
| --- | --- | --- | --- |
| Employees | Create/edit employment & education | POST /employees; PATCH /employees/:id | Unique case-insensitive email; valid dates, supported departments and nonnegative previous experience; default new role Employee |
| Confidential | Edit personal/bank information | PATCH /employees/:id/confidential | Separate grant and field allowlist; exclude values from general APIs; never audit full bank/NID values |
| Assets | Add/edit identity & correct dates | POST /assets; PATCH /assets/:id | Unique serial, chronological actual dates, retained correction history |
| Assign/return | Link exact device; return/repair | POST /assets/:id/assignments; POST /assignments/:id/return | Active recipient, atomic availability check, no double assignment, preserve previous assignment |
| Leave | Create/edit request | POST /leave; PATCH /leave/:id | Calendar-year allowance, approved+pending reservation, no overlap, inclusive working days; edits return to Pending |
| Leave decision | Approve/decline | POST /leave/:id/decisions | Revalidate balance and documentation inside transaction; actor/decision history; no silent self-approval policy assumptions |
| Medical document | Upload/read | POST /leave/:id/documents; GET authorized signed download | Private storage; ownership and HR permission; MIME/size checks, scanning, expiration, retention; demo stores filename only |
| Daily login | Create/resume workday | POST /workdays/entry | Server clock, idempotent employee+date key, timezone Asia/Dhaka, do not restart closed or overwrite prior open day |
| Daily work | Break/resume/updates/sign-out | POST /workdays/:id/events; POST /updates | Event transactions, net-work intervals, saved update revisions and exception reasons |
| Daily corrections | Text/evidence/time corrections | POST /daily/:id/corrections | Preserve prior values, no negative time, return to Pending review; content and time permissions enforced |
| HR review | Excuse/mark missing | POST /daily/:id/decisions | Authorized HR, immutable decision log; missing updates and short hours distinct |
| Archives | Archive/edit metadata/restore | POST /employees/:id/offboarding; PATCH /archives/:id; POST restore | Suspend access, remove from active directory, retain outstanding asset follow-up; restore with Employee role |
| Retention | Keep/delete | POST /archives/:id/retention; DELETE /archives/:id | At least 30 calendar days, reason+explicit confirmation, dependency checks; no auto deletion |
| Insurance | Configure source projection | PATCH /integrations/insurance/settings | Allowlisted source, secrets outside browser, source tracker is authoritative, no duplicate manual entry |
| Insurance fixture editor | Review source correction flow | No production duplicate endpoint | Edit source tracker via its existing authorized workflow then sync sanitized projection |
| Policies | Medical threshold/reminder preference/page size/notes | PATCH /module-settings/:module | Configuration grant AND module grant; version policy, retain actor/reason; approved constants cannot change via free text |
| Communications | Create/edit announcements/templates | POST/PATCH /announcements; PATCH /notification-templates/:kind | Communications grant, safe template token allowlist, sanitized content/audience; no executable HTML |
| Access | Role/grant/suspension | PATCH /accounts/:id/access | Super Admin only; no self-demotion/suspension, preserve an active Super Admin, clear grants on Employee downgrade |
| Audit/reports | Read/export | GET /audit; GET /daily/export | Read-only audit, module permission, bounded queries, CSV formula escaping, no confidential fields in directory exports |
| Performance | Placeholder | Defer contract | No scoring system before approved framework |

## Common data model

Employee (24 profile fields plus derived experience); ConfidentialEmployeeDetails; AccountRoleGrant; Asset; AssetAssignment; AssetCorrection; LeaveRequest; LeaveDecision; LeaveDocument; LeavePolicyVersion; DailyWorkday; WorkInterval; DailyUpdateRevision; DailyCorrection; ExceptionDecision; OffboardingRecord; RetentionDecision; NotificationTemplate; Announcement; ModuleSettings; InsuranceProjection; AuditEvent.

Production can normalize these according to the existing schema. Avoid replacing the current employee/leave identity system or introducing a second employee-management database.

## Conflicts and consistency

PATCH requires expected version/ETag. Reject conflicts with a reload-and-review path. Device assignment uses a lock/unique open-assignment constraint. Leave decisions reserve finite balances transactionally and re-check current policy. Time events use server timestamps; tab concurrency cannot double-count. Only one close operation is allowed per workday; closing preserves previous open intervals. Returning to the portal on the same date resumes state, including breaks and drafts.

## Insurance projection

Employee fields are an explicit allowlist: reference, masked last-four member ID+suffix, type, amount paid, start basis/date, insurer receipt, settlement, confirmed bank receipt, valid stage/total durations. Exclude names, documents, pending/unconfirmed rows. Actual submission start takes precedence when available; otherwise HR approval. Friday/Saturday excluded, same-day stages zero, no public holiday adjustment in this version. Record actual rejections separately from >30-working-day overdue classification. Date filters use bank date for completed and recorded start for rejection/overdue counts. Calculate averages before rounding. Preserve last successful snapshot and timestamp on refresh failure.

## Reminders and branding

The demo emits in-app checkpoint reminders while the portal is open, using approved-leave/weekend exclusions, and provides a full eligibility preview. Production scheduler must use the same policy, skip inactive employees/approved leave/non-working days, deduplicate by employee+workday+checkpoint, and deliver through the existing notification service. There is no new Teams integration. Fixed 8h and 4h rules are authoritative; no late-start penalty. Flexible schedules need an approved deadline before a job can label a never-signed-in employee as missing.

## Acceptance before production

Port and test the full employee -> administrative edit -> permission-filtered read flow. Verify concurrent balance/device changes, unauthorized direct API access, confidential response omissions, cross-year leave, document access, closed/overnight workdays, correction audit, source refresh failures and notification deduplication. Document backups/retention and recovery. Demo tests are rule checks, not evidence of completed production integration.
