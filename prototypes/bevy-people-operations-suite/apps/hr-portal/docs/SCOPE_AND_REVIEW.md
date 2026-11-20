## Current review · 11 November 2026

See PORTAL_REVIEW_2026-11-11.md for the full current section map. Expense scope section 12 is implemented as a shared browser-local module: HR / Super Admin validation only; no manager/employee approval. The Build guide, permissions summary and payroll handoff now reflect this. See EXPENSE_MODULE.md and EXPENSE_PAYROLL_RUNBOOK.md. Older dated notes below remain historical; production integrations are still pending.

# Scope coverage and acceptance walkthrough

Source: current customization document read 5 November 2026.

| Section | Demo implementation | Integration remaining |
| --- | --- | --- |
| 1 Remove modules | Unneeded menus omitted | Safely disable modules and check dependencies in existing portal |
| 2 Branding | Shell, title, favicon, branded access screen | Replace live branding and system email/notification templates |
| 3 Profile | All personal/job/education fields, editable samples, automatic completed-month experience | Schema migration, validation, real permissions |
| 4 Bank confidentiality | HR-only simulated view, obvious demo values | Server field isolation and audit access |
| 5 Search | Name/email plus department, position, type, manager, location; archive separate | Indexed server search/pagination |
| 6 Assets | Unique device serials, assignment/profile link, return/repair, optional return until returned | Transactional assignment history and concurrency protection |
| 7 Offboarding | Archive, restore, keep, typed deletion after 30 days, assigned-device deletion block | Durable audit, retention authorization, related-record policy |
| 8 Speed | Lightweight dependency-free UI and responsive cards | Profile production queries, caches and slow screens |
| 9 Insurance | Confirmed claims, masked IDs, filters, stage averages, 10/25/all, refresh/failure preview | Connect approved sanitized tracker data; support actual submission basis |
| 10 Performance | Available future placeholder | Await final framework |
| 11 Daily Updates | Included: portal-entry automatic clock, updates, exception reasons/review, history, CSV | Backend accounts/leave/revisions/scheduling/ownership |

## Review order

1. HR → Employees → search `ariana` or `ariana.1@example.com`. Clear and test each filter. Open personal/confidential tab; edit a fictional record.
2. Assigned assets → assign available serial. Check that it appears in that profile. Assets → return it. Reassign returned device.
3. Offboard a sample record. Check it disappears from active list. In Archives, test an 8-day sample versus a 32+-day sample. No auto delete occurs. Delete requires typed ID; assigned devices block deletion.
4. Leave → request and approve a sample. These records provide leave-reuse context for Daily Updates.
5. Insurance → select each period, choose month, custom range, search suffix/member, choose 25/all, open timeline. HR tracker → simulate failure → see stale-data notice and unchanged success time. Restore success.
6. Employee preview → directory/admin navigation gone; own profile/assets and sanitized claims remain. Super Admin → all granted administrative tools and confidential details present. HR Admin → only delegated modules; Employee → own workspace only.
7. Build guide → 4h scenario → Daily Updates → submit/edit Mid-Day, pause/resume. 8h scenario → missed reason or normal Mid-Day → EOD → sign-out. See missing/short-hour flags separately; review exceptions as HR; export team reports. Scenario controls live in Build guide only. Portal entry starts the normal workday automatically; refresh must retain it.
8. Build guide → add and export feedback notes. Reset restores original data. Test reload persistence in the same browser.
9. At a narrow viewport, verify navigation toggle, stacked employee/claim cards, forms, filters and pagination. Use keyboard navigation and Escape to close dialogs.

## Known limits

- No real backend, shared edits, medical files, insurer APIs, payroll or recruitment connections.
- Browser-local demo state can be modified or cleared by its user. Role switch is presentation only.
- The Bevy SVG logo is reused from the owner’s Daily Updates reference; the palette matches its #008080 teal and #103e40 dark teal.
- Local server requires Python. Hosted review requires a ChatGPT account using company email.
- The current production HR portal was not modified or audited in this task.

## Updated audit

See SCOPE_AUDIT.md for the full source-to-demo mapping, including the Employee Status filter and all section 3/4 fields. Control centre demonstrates record edits and HR-delegated module configuration/communications. See ADMIN_BACKEND_BLUEPRINT.md for the production API and persistence boundaries.
