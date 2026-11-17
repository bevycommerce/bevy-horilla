# Bevy Daily Updates — focused HR portal module

A Bevy-branded workday module with **HH:MM:SS timers**, automatic break accounting, a daily activity thread, department-neutral updates and weekly/monthly reporting. The main experience is My day / History; HR gets Team view / Reports. Standalone pilot tools are kept behind the setup icon.

The supplied New Daily Updates Flow is reflected in the format: dated/timezone sign-in; progress bullets and work evidence; Mid-Day near four hours; EOD 30–45 minutes before finishing; feedback availability; a closing sign-out message; and break/return events. Work beyond eight hours continues to be recorded.

See **[HR_PORTAL_MODULE.md](HR_PORTAL_MODULE.md)** for the PM handoff, pilot gate and future integration boundary.

## v4 changes and database upgrade

- Clean horizontal module layout; official Bevy wordmark and teal accent.
- Second-precision working, break, elapsed and extra-time timers, date and timezone.
- One update composer with Mid-Day / EOD tabs; work links, blockers and support person.
- Current-browser-session draft recovery, server submission records and revision history.
- EOD can be submitted before eight hours to allow the reference handover window. Signing out still checks the hours target and a minimum 30-minute feedback window; exceptional closes need a reason and remain visible for review.
- Weekly reports and monthly reports grouped by week; summary and daily-detail CSV exports.
- Explicit fictional sample day for PM review. No production employee data is seeded.

**Existing v3 database:** apply `upgrade_v3_to_v4.sql` only. **Existing v2:** apply `upgrade_v2_to_v3.sql`, then `upgrade_v3_to_v4.sql`. **New database:** run `schema.sql` once. Original update, session, leave and audit records are preserved. `upgrade_v1_to_v2.sql` is retained for legacy installs.

The website is still a setup preview until the company database is connected in `config.js`. A live staff pilot needs invite-only authentication, real roster authorization and two-account isolation checks. Leave sync, existing HR-portal SSO and background email reminders are not connected by a frontend link or flag.

## Current delivery state

- GitHub source and automated test/deployment workflow are provided in this repository.
- `config.js` has no database URL/key yet: the website opens in explicitly labelled, browser-local **setup preview** mode.
- Real employee login, persistent shared records and HR access require your company Supabase project connection. Preview data is not production data.
- Employee roster starts empty. No employee data is stored in this public repository.
- The existing HR portal remains responsible for leave requests/approvals. Its link is provided; automatic leave sync is not configured.

## Employee flow

1. Log in to the invited account. This authenticates the account but does not start work.
2. **Start my working day** whenever work starts. Only one open work session is allowed per employee, with one session per work date.
3. **Start break / Resume work** excludes breaks from net working hours. Closing the tab does not reset the clock.
4. At four net hours, Mid-Day becomes due. Submit progress, next steps and blockers.
5. If Mid-Day cannot be provided, choose **Unable to give Mid-Day update?** and supply a category and explanation. It is **pending HR review**, not automatically excused.
6. Before finishing, submit EOD, remain available for 30–45 minutes, then **Sign out of work**. EOD requires Mid-Day or a recorded pending/accepted exception (or an imported half-day exemption).
7. If the day must end before eight hours or before the feedback window completes, record an explicit reason in the closing summary. EOD remains required. The hours shortfall and review status remain visible to HR.

Signing out of the account is separate from signing out of work. Active overnight work stays on its sign-in date. Forgotten sessions open over 18 hours are flagged for review, not treated as a verified eight-hour day.

The timer records declared working sessions; it does not prove productivity. No employment decisions, payroll or attendance penalties are automated.

## HR flow

- **Overview:** employee/date/department filters, work-session hours, Mid-Day, EOD and overall update status.
- **Employees:** add supplied roster records, working days, timezone, join/end dates and roles.
- **Work sessions:** review recorded time, breaks and short days. Correct a forgotten/mistaken sign-in or sign-out with a mandatory reason. Before/after values are retained in an append-only audit trail.
- **Exception reviews:** accept or decline Mid-Day reasons with a review note. Accepted reasons remain visibly labelled as exceptions; declined reasons do not count as submitted updates.
- **Reports:** date-range totals, submitted/excused/outstanding checkpoints, complete/partial/no-update days, recorded time, eight-hour days and session review counts. CSV export is available.
- **History:** view submissions and text revisions. First submission time is preserved.

Update completion and hours completion are distinct. An accepted Mid-Day reason plus EOD can complete update compliance while a short working day still requires review.

## Security and persistence

- Invite-only Supabase Auth with verified emails. Disable public sign-up before rollout.
- Database row-level security restricts employees to their own records and allows authorized HR profiles to see the workspace.
- Browser users cannot directly insert or edit session clocks, audit events, updates or exception decisions. Security-definer RPCs validate identity and assign server timestamps.
- Duplicate sessions and updates are guarded by database uniqueness constraints and transaction locks.
- HR cannot remove their own HR access in the portal.
- Only the browser-safe project URL and publishable/anon key belong in `config.js`. **Never put a service-role key, database password, employee exports or private HR data in GitHub.**
- Historical roster/workday changes and imported leave approvals can recalculate reports; export a final monthly snapshot when needed.

## GitHub deployment

The repository keeps the existing flat file layout. `.github/workflows/pages.yml` runs syntax, logic and PostgreSQL tests, stages **only** `index.html`, `app.js`, `logic.js`, `styles.css`, `config.js` and `bevy-logo.svg`, then deploys with GitHub Pages.

Repository Settings → Pages → Source must be **GitHub Actions**. Pushes to `main` and manual workflow runs trigger the pipeline. A successful deployment exposes its exact site URL in Actions/Pages.

No build step, Teams permissions or employee data are needed to publish the setup preview.

## Connect the live database

Use a company-owned Supabase project. A connection is required before using the tracker with employees.

### Fresh database

Run **`schema.sql` once** in the new project's SQL Editor. It installs the base schema plus the v3 session/exception and v4 focused-module extensions. Do not run the fresh installer on an already configured database.

### Existing v2 database

Run **`upgrade_v2_to_v3.sql` then `upgrade_v3_to_v4.sql`**. Existing employees, updates, leave records and revision history are retained. New work-session and exception tables are added; the submission RPC is upgraded to require a work session. Old updates remain readable.

If you installed v1 instead, first run the existing `upgrade_v1_to_v2.sql`, then `upgrade_v2_to_v3.sql` and `upgrade_v3_to_v4.sql`. Back up a live database before upgrades.

### Authentication and first HR profile

1. Disable public sign-up and keep email verification enabled.
2. Set Auth Site URL and allowed Redirect URLs to the exact deployed GitHub Pages URL, including repository path.
3. Configure company SMTP before inviting staff broadly; provider delivery limits apply.
4. Invite the HR email in Supabase Authentication.
5. Insert the first HR employee using privileged SQL Editor access:

```sql
insert into public.employees
(email, full_name, department, country, role, join_date, timezone, workdays)
values
('YOUR_VERIFIED_HR_EMAIL', 'YOUR_NAME', 'Human Resources', 'Bangladesh', 'hr', current_date, 'Asia/Dhaka', array[1,2,3,4,5]);
```

Use the exact lower-case verified email. No live HR or employee accounts are created by this source package.

6. Fill `supabaseUrl` and `supabaseAnonKey` in **`config.js`**, preserving the HR portal URL, and push the change.
7. Log in as HR, add the actual employee data when provided, and invite each matching email through Supabase Authentication. Creating a profile alone does not send an invitation.
8. Invitation/recovery links lead to password setup. Employees set their own passwords.

Check current hosting/database free-plan, inactivity and email limits; this repository does not purchase or activate a paid plan.

## Leave and reminders

Leave stays in the existing HR portal. The local read-only exemption tables are integration targets, not a second approval system. Approved leave must be imported by an authorized backend before the tracker can exclude it. Until that connection is implemented, the dashboard says leave exclusion is not connected and reports should be treated as provisional.

Full imported leave excludes both updates. Half imported leave excludes Mid-Day only under the inherited policy; confirm any reduced-hours policy before enabling half-day integration. The default daily work target remains eight hours.

In-app due notices and optional browser notifications operate while the page is open. Background email/push reminders and scheduled email reports are **not configured**. No Teams sync is present.

## Verification

```sh
npm ci --ignore-scripts
npm run check
npm test
npm run test:database
```

Tests cover 4/8-hour checkpoints, breaks, ended/overnight/stale sessions, pending versus accepted/declined reasons, leave exemptions, isolated data access, protected clocks, EOD requirements, short-day recording, correction audit, revision history and anonymous-access denial.

Before employee rollout, run the complete flow against the configured Supabase project with HR plus two test employee accounts. Verify employee A cannot read B's records, notifications do not duplicate, invitation/reset redirects work on the final URL and approved leave matches the existing HR portal.

## Remaining integrations

- Company Supabase project and account invitations.
- Actual roster, supplied later.
- Existing HR portal approved-leave data connection.
- Optional scheduled email reminders, if desired.
