# Roles, delegated access and UI handoff

Owner direction, 5 November 2026: consolidate the separate HR/management view into three clear roles: **Super Admin**, **HR Admin**, **Employee**. A person's department or job title does not itself grant access.

## Role boundaries

| Capability | Super Admin | HR Admin | Employee |
| --- | --- | --- | --- |
| Own workday, updates, history and profile | Yes | Yes | Own only |
| Assigned device details | Own + inventory | Own + inventory if assigned | Own only |
| Employee directory and editing | Full | Employee management grant | No |
| Bank, NID and sensitive personal fields | Full | Confidential grant AND employee management | No |
| Device inventory and assignment | Full | Asset management grant | No |
| Leave approval | Full | Leave approvals grant | Own requests only |
| Pending/unconfirmed insurance tracker | Full | Insurance tracker grant | No |
| Sanitized confirmed insurance dashboard | Yes | Yes | Yes |
| Daily team records, reports, exports, exception decisions | Full | Daily reports & review grant | No |
| Archives, retention and deletion | Full | Employee archives grant | No |
| Administrative change history | Full | Activity log grant | No |
| Assign roles, delegate modules, suspend accounts | Yes | No | No |
| Portal rules overview and announcements | Manage | Read relevant announcements | Read relevant announcements |

HR module grants are explicit, independent capabilities defined in `web/permissions.mjs`. Employees never inherit admin grants. Super Admin always has full access. Suspending a sample account disables its preview selection and administrative policy checks.

## Assignment flow

1. Super Admin opens Access management and finds an existing active employee account.
2. Manage access → choose role and Active/Suspended status.
3. If HR Admin, select the modules to delegate. Confidential details require Employee management.
4. Enter a reason and save. The audit event records actor, employee, role/status and reason context.
5. Preview the employee account to confirm the menus, sensitive fields and actions match the chosen policy.

The active Super Admin cannot demote or suspend themselves. The policy retains at least one active Super Admin. Offboarding an active Super Admin is blocked until responsibility is reassigned; self-offboarding must be performed by another authorized administrator. Offboarding suspends the related fictional account; restoring an archived record restores Employee access, with administrative grants requiring a fresh Super Admin decision.

## Important demo boundary

These assignments modify only fictional accounts in the current browser. They do not invite real users, send mail, edit company identity providers, grant GitHub access or change the outer Site audience. The hosted demo still checks an exact authenticated bevycommerce.com email domain before delivering any asset. The role selector is labelled Demo view and intentionally lets reviewers compare sample personas. It is not an authentication or privilege-escalation mechanism for production.

Each sample persona has a separate working session/draft container so switching review roles does not overwrite another sample user's clock, break or drafts. Real production sessions need identity-bound server storage and trusted server time.

## Backend implementation requirements

Reuse the existing portal accounts. Persist role assignment, status, module grants, change reason and actor/time in an auditable database. Authorize every route, field, mutation, export and file download server-side. Prevent self-lockout and last-Super-Admin removal transactionally. Revoke sessions/cached permissions on suspension. Do not send bank/NID fields to unauthorized clients. Do not trust a browser role, arbitrary email header or localStorage record. Keep hosting/domain access separate from application HR authorization.

## Additional experience improvements

- Navigation grouped into Your work, People operations and Administration.
- Super Admin and HR Admin have a consistent administrative UI; only delegated capabilities differ.
- Global quick search finds authorized pages and, with Employee management, colleagues. Ctrl/Cmd+K opens it.
- Attention centre derives outstanding leave reviews, daily exceptions, due Mid-Day updates and archive decisions from current sample data.
- Super Admin can pin sample announcements for everyone or administrators; only the selected audience sees them on the dashboard.
- Build guide contains a short review path, role matrix, scope status, implementation map, reviewer scenarios and exportable feedback notes.
- Performance remains future scope; no payroll/recruitment modules or unapproved review framework were added.

## Current control centre grants

Control centre is visible to Super Admin and HR Admin. Each card's record actions require the relevant module permission. `configuration` permits policy/configuration edits only alongside that module grant. `communications` permits announcement and notification-template edits. Only Super Admin can grant/revoke these permissions or manage access. Existing preview accounts retain previous permissions; new demo workspaces seed full grants for sample HR Admins. A limited existing HR Admin can receive the new grants through Access management.
