# Daily Updates module — PM handoff

## Product scope

One focused Daily Updates module inside the existing Bevy HR portal. Reuse portal employee identities, roles, reporting lines, working days and approved leave. Do not create a second employee directory or leave-approval workflow.

Default navigation: **My day, History**. Authorized HR gets **Team view, Reports**. Pilot-only roster, corrections, exceptions and connection controls are behind the setup icon; `BEVY_CONFIG.embeddedMode = true` hides pilot administration from the header.

## Employee journey

1. Sign in to work at a flexible time. Generate a dated thread entry with sign-in time and timezone.
2. Timer displays **HH:MM:SS**, net working time, accumulated breaks, total elapsed and time beyond eight hours.
3. Taking a break pauses net work. Returning resumes it; actual break duration is calculated automatically and both events appear in the thread.
4. At around four net hours, share completed/current tasks as bullets, relevant work links, next priorities and blockers/support contact.
5. If Mid-Day is missed due to pressure, meetings, power/internet issues or another reason, record a short note. Pending/accepted/declined states remain distinct; EOD remains required.
6. Share EOD **30–45 minutes before finishing**, as in the supplied New Daily Updates Flow. The eight-hour target is a separate hours check. Work may continue beyond eight hours and is not automatically stopped.
7. Before signing out, review a closing summary: net work, total breaks and time beyond eight hours. Append a closing note and sign-out event to the same thread.

The server flags an exceptional close if work is under eight hours, the minimum 30-minute feedback window after the latest EOD has not completed, or the session has been open over 18 hours. A reason is required; no automatic payroll/disciplinary decision is made.

## Department-neutral update format

- Completed tasks / progress: one item per line, with status or outcome.
- Work links & evidence: ClickUp, GitHub/PR, Figma, Google Docs/Sheets, campaign results, QA evidence or screenshot links.
- Remaining work / next priorities.
- Blockers and person/reporting manager who can help.

Developers still follow their existing code-commit process. This module records links; it does not push company code or send messages to other systems.

## Reports and retention

Weekly report or monthly report broken into Monday-based weeks. Per employee/week: net working time, break time, extra time beyond eight hours, Mid-Day/EOD submission counts, exceptions and review flags. Export weekly summaries or full daily detail with update text, links, timestamps, notes and closing context.

Shared records persist in Postgres after the pilot database is connected. Browser preview/sample data is not shared storage. No records are automatically purged. Agree a retention period and backup/access policy with the HR portal owner before production rollout.

Drafts are saved in the current browser session and cleared on account logout. Submitted records have server timestamps and revision history. Audit clocks and imported leave remain separate from editable update text.

## Integration boundary

A frontend flag only changes presentation; it does not grant access or integrate authentication. The host portal must supply/bridge authenticated identity through a trusted backend and enforce employee/HR authorization server-side.

The current pilot uses verified Supabase identities and database RLS. For integration, either retain that authorization boundary with an approved identity bridge or port the documented RPC/data contract to the existing HR portal backend. Never pass an HR role or employee ID from browser input as trusted identity. Do not put HR portal credentials or service-role keys in the website.

Required entities: employee identity and working days; work session + break events; update + revisions; Mid-Day exception + decision history; approved leave/holiday read model. Existing module SQL and policies provide the pilot implementation.

Approved leave is not yet synced. A navigation link alone is not leave synchronization. When connected, import approvals, cancellations and freshness metadata; mark reports provisional if leave data is stale.

## Pilot gate

Before staff use: connect the company database; apply the correct schema/migration; configure invite-only authentication and redirect URLs; authorize the HR account; add the supplied test roster; verify two-employee isolation and the complete clock/update/report flow. No paid service or employee account is created by the source code.

The public website currently supports an explicitly labelled fictional sample day for PM design review. Production login/shared records are not active until the database is connected. Notifications work while the page is open; background email/push is not configured. Offline drafts remain local; clock-write failures need a connection and, when appropriate, an audited HR correction.

## Access v5
Employees see only My day and their own History. Explicit `management` accounts can read Team view and Reports but cannot administer staff, correct sessions or approve exceptions. Only `hr` accounts administer. No role is inferred from department, title, email domain or URL. Production roles come from the server roster. Apply upgrade_v4_to_v5.sql after the v4 migration. Public preview role switching affects fictional browser-local data only.
