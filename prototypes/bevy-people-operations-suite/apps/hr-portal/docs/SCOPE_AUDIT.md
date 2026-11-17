## Current review · 11 November 2026

See PORTAL_REVIEW_2026-11-11.md for the full current section map. Expense scope section 12 is implemented as a shared browser-local module: HR / Super Admin validation only; no manager/employee approval. The Build guide, permissions summary and payroll handoff now reflect this. See EXPENSE_MODULE.md and EXPENSE_PAYROLL_RUNBOOK.md. Older dated notes below remain historical; production integrations are still pending.

# Scope audit and acceptance map — 5 November 2026

Source: Bevy Commerce Internal HR Portal – Customization Requirements, Google Doc 1v7tDZexmSurGniqddMdhMUqand4xyscRGW5tjsDaDg4. Read directly on 5 November 2026. Later owner instructions supersede the document's Future label for Daily Updates and its older management role wording. Current roles are Super Admin, HR Admin, Employee.

## Employee profile: sections 3 and 4

All requested fields were present in the previous data model. This revision makes their coverage explicit, reorganizes the editor, improves validation, and centralizes the schema in `web/profile-schema.mjs`. No field from the scope is removed.

| Group | Every required field | Demo location |
| --- | --- | --- |
| Personal (10) | Full Name; Address; Company Email; Personal Email; WhatsApp Phone Number; Emergency Phone Number; Blood Group; Gender; Date of Birth; NID/Passport Number | Personal & confidential tab; Personal information editor section |
| Employment (6) | Joining Date at Bevy; Position; Department; Employee Type; Reporting Manager; Work Location | Overview; Employment information editor section |
| Education/previous experience (2) | University-level Education Qualification; Previous Work Experience before joining Bevy | Overview; Education & experience editor section |
| Automatic experience (2 derived) | Bevy Experience; Total Work Experience | Overview; completed months calculated from joining date/current date + previous months |
| Bank (6) | Bank Name; Branch Name; Account Holder Name; Account Number; Routing Number; SWIFT/BIC if applicable | Personal & confidential tab; Confidential bank information editor section |

24 stored fields plus 2 derived values. Completion count is 23 because SWIFT/BIC is optional. Completion is a data-maintenance indicator, not a claim that every field is mandatory at onboarding. All eight requested departments are present: Engineering, QA, HR, Marketing, Project Management, Product Management, Design, Top Management. Employment type is separate from the removed Work Type module.

Private identifiers, personal details and banking require the Confidential details grant (which requires Employee management). Employee profile overview contains employment and education only. Production must omit confidential values from unauthorized API responses entirely.

## Full scope audit

| Section | Interactive coverage | Production boundary |
| --- | --- | --- |
| 1 Remove modules | Recruitment, payroll, allowances/deductions, payroll history, salary, shift information, work type, tags, employee asset requests absent | Remove/hide modules in the existing portal, check dependencies |
| 2 Bevy branding | Logo, portal name, login preview, title/favicon, navigation, branded notification/email previews with editable templates | Replace production login and server notification templates |
| 3 Profile | All fields above; grouped edit form, completeness, duplicate email/date/experience validation, automatic experience | API field authorization, schema migration and server validation |
| 4 Bank confidentiality | All six bank fields; restricted personal/bank tab and editor | Separate protected endpoints/models and encrypted storage as applicable |
| 5 Search | Name and company email; department, position, type, manager, location AND status filter | Bounded indexed search, pagination, authorized archive queries |
| 6 Assets | Exact device/model/serial; create/edit, assign/return, repair, date correction, profile linkage, history | Atomic assignment transaction, unique serial, durable assignment history |
| 7 Offboarding | Remove from active list, HR archive, date/note correction, retain/delete after 30 days, no auto delete, typed confirmation, outstanding-device guard | Retention/deletion dependency handling; durable audit and recovery policy |
| 8 Usability | Compact Bevy layout, quick search, responsive cards, explicit form groups, local low-latency operations | Profile the production API/database; demo speed is not a production benchmark |
| 9 Insurance | Confirmed-only reporting; reference/member search, ID masking, stages/averages, rejection vs overdue distinction, date filters, 10/25/all, refresh/failure state; fictional row correction for review | Existing tracker remains source of truth. Source mapping is configurable but no live connector is implemented. No medical files in employee reporting |
| 10 Performance | Module retained with clear future status | Wait for final performance framework; no invented scoring |
| 11 Daily Updates | Included per later instruction: login clock, breaks, reference composer, drafts, revisions, exceptions/review, time corrections, history, period reports/CSV; in-app reminder eligibility excludes approved leave/weekends | Server time, session concurrency, shared storage, actual leave calendar and unattended reminder delivery |
| Later leave policy | Vacation 11; Floater Day 3; unlimited Sick Leave; Jan–Dec no accrual/carry-over; balance/overlap validation; medical threshold 2 or 3 configurable | Confirm provisional >2-day documentation rule before production; private upload pipeline |
| Later admin request | Control centre, per-module record edits, settings/configuration, announcements/template edits, delegated permissions | Actual authenticated APIs, durable writes and server authorization |

## Gaps closed in this revision

Employee Status filter; visible scope/field checklist in Build guide (previously the mapping existed in source but was not rendered); grouped profile editor and validation; inventory identity/date correction/history; leave correction with re-approval; daily time/full-content correction with retained values; archive metadata correction/retention history; editable sample tracker rows; module settings; HR-delegated Configuration and Communications; notification previews/template edits; shared leave-aware in-app reminder eligibility; robust last-four-digit member masking; sample persona preserved on reload.

## Review examples

- Employees -> filter Archived -> inspect sample profile (archive grant required).
- Profile -> Edit -> four field groups -> save fictional education -> Overview updates.
- Assets -> Edit details -> correction reason -> History; status/employee linkage remains.
- Leave -> Edit request -> new date/type -> Pending -> approve; finite balances revalidate.
- Insurance -> Edit sample -> Completed without bank confirmation -> blocked. Valid dates+confirmation -> appears in employee reporting.
- Daily Updates -> Team -> Adjust time -> reason -> Pending review -> Details shows previous values. Correct text/evidence/next steps/blockers/support separately.
- Archives -> Edit archive -> correct date/note -> retention recalculates; Keep archived retains offboarding note.
- Control centre -> Module settings -> medical threshold/reminders/report page size -> changed preview behavior. Notes for fixed policies do not silently alter approved policy constants.
- Super Admin -> Access management -> HR Admin -> Configuration/Communications + allowed modules -> Preview -> control centre limited accordingly.
- Build guide -> Reminder eligibility -> approved leave/non-working day suppressed; Preview messages shows Bevy identity and edited templates.

Demo mutations are browser-local and never update the current production HR portal, Drive tracker, real employee accounts or actual emails. The site retains the existing server company-domain access gate. This is a build blueprint, not a production backend or a security certification.
