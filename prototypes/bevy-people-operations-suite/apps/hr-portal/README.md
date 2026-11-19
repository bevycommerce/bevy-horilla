## Payroll v4.1

One-time payroll email setup → select period → Sync expenses. Saved mapping, normalized email checks, immutable ID snapshots and safe retry are shared with the standalone demo. Google auto-write remains simulated; CSV is functional.

## Payroll v4 · 12 November 2026

Expenses → Payroll sync now offers period selection, explicit eligibility reasons, Late unpaid totals, frozen multi-employee runs, ready CSV and guarded salary-sheet formulas. See docs/EXPENSE_PAYROLL_RUNBOOK.md. Private named access remains unchanged.

## Portal review · 11 November 2026

Build guide updated to all 12 scope sections with current HR / Super Admin-only expense validation, payroll handoff and test datasets. See docs/PORTAL_REVIEW_2026-11-11.md. Existing modules and layout are retained.

## Expense module v3 update

Only HR / Super Admin validates. Employee/manager reviews removed. Expanded fictional scenarios and zero-expense mode are in Controls & tests. Payroll sync includes operator instructions; see docs/EXPENSE_PAYROLL_RUNBOOK.md. These rules supersede older expense routing notes below.

# Bevy Commerce Internal HR Portal — interactive prototype

A reusable, private review prototype for the current HR Portal customization scope. **Fictional data only. This is not a production HR system.**

## Quick start on your computer

1. Download this private repository (Code → Download ZIP) and extract it.
2. Install Python 3 from python.org if it is not already available.
3. Windows: double-click `start-demo.bat`. macOS: run `sh start-demo.command`. Linux/macOS terminal: `python3 serve.py`.
4. Open **http://127.0.0.1:8080**. Keep the terminal open. Stop with Ctrl+C.

No Node packages or installation are needed to run the demo. Opening `web/index.html` directly is not supported because browsers restrict ES modules on file URLs.

The local server binds only to your computer's loopback address. Sending this localhost link to someone else will not open your PC. See [Hosting and access](docs/HOSTING_AND_ACCESS.md) for sharing.

## Test data

- 64 fictional employees: 56 active, 8 archived, all eight departments, three locations, contract/full-time, varying experience.
- 36 devices: assigned, available, returned and repair; unique obvious demo serials.
- 96 insurance records: 65 completed, plus insurer-rejected, pending, overdue and unconfirmed samples.
- 16 leave requests and 70 historical daily records with submitted, missing, pending-review, excused and short-hours cases.
- Dates are generated relative to first initialization. Reset in Build guide to refresh the seed.

## Interactive flows

Employee search/filter, profile edits and experience calculations; asset creation, assignment and actual return; offboarding, archive retention and restore/delete; leave requests and approval; insurance timeline, period/search filters, 10/25/all pagination and refresh failure simulation; role previews; Daily Update clock, pause/resume, Mid-Day, EOD, exception review, history and CSV export; review notes, print, reset and activity trail.

Use **Preview as** to compare Super Admin, HR Admin and Employee. All fictional data and changes live in localStorage in each browser. The role selector demonstrates the desired UI: it is not production authorization. Different reviewers do not share changes. Export review notes or CSVs to communicate feedback.

## Source map

| Path | Purpose |
| --- | --- |
| `web/index.html` | Accessible app shell and branded metadata |
| `web/styles.css` | Responsive layout, components, mobile table cards and print styles |
| `web/app.js` | Views, dialogs, demo actions, browser persistence, CSV exports |
| `web/seed.mjs` | Deterministic fictional fixtures relative to initialization date |
| `web/domain.mjs` | Pure experience, date, claim, time and asset rules |
| `web/permissions.mjs` | Three-role policy, HR module grants and access-change safeguards |
| `worker/gate.mjs` | Hosted request authorization and response security headers |
| `scripts/build.mjs` | Embeds every frontend asset behind the Worker access gate |
| `serve.py` | Loopback-only static local server with security headers |
| `tests/` | Meaningful domain and access-boundary tests |
| `docs/` | Scope, implementation architecture, security, hosting and QA handoff |

## Validation and build

Node 22+ is sufficient; no dependencies:

```sh
npm run check
npm test
npm run build
```

Build produces `dist/server/index.js` and `dist/.openai/hosting.json`. No public static asset directory is deployed. Each asset is returned only after the same server-side domain check as the HTML page.

## Hosted access design

The outer hosting route permits visitors to reach the sign-in screen. The Worker requires a Sites-authenticated user ID **and** an exact `bevycommerce.com` email domain before it returns any demo HTML, JavaScript, CSS, SVG or seed data. Anonymous requests receive a login screen (401); other domains receive an account-switch screen (403). All protected responses are `private, no-store`.

Reviewers need ChatGPT accounts using their company email. No individual invitations or shared password are used. Company-domain access intentionally allows any authenticated company account to review this fictional prototype. If access must be limited to only PMs/developers, use a verified identity-provider group instead; domain matching alone cannot identify departments.

The domain gate relies on Sites' trusted authentication ingress and its identity headers. **Do not deploy the Worker directly on another host without replacing this integration with verified identity middleware.** Local `serve.py` does not implement login; it is reachable only from the same computer by default.

## Production integration

Reuse the existing portal's accounts, roles, leave records and database. Do not ship localStorage persistence, the role selector, scenario buttons or fake identifiers into production. The source is an interaction reference and reusable UI/domain code; it is not a drop-in backend replacement. See [developer handoff](docs/DEVELOPER_HANDOFF.md).

Original scope: https://example.com/configure-internal-source

No real employee, bank, identity, contact or medical data is included. No third-party scripts, remote fonts, analytics, tracking, database connections or live HR API calls.

## 5 November revision: Daily Updates included now

Daily Updates is a current module. Entering the authenticated portal starts the fictional working day automatically; there is no separate start button. Refresh/re-entry resumes the same session, including breaks and saved drafts. A closed day stays closed. An open overnight session must be closed explicitly before the next day starts. The reference-style inline composer, task-per-line progress, multiline evidence, next priorities, blockers, support person, category/note breaks, day thread, summary, history and reports are integrated. Scenario controls are confined to Build guide. The dashboard is streamlined and the actual Bevy SVG and teal palette are applied across the portal and access screen.

These are browser-persistent demo flows. Production portal sign-in events, trusted server time and shared durable daily records still require the existing portal backend integration described in the handoff.

## Administrative roles and reviewer polish

The current role model is Super Admin / HR Admin / Employee. Super Admin owns Access management, role assignment, HR module delegation, account suspension and portal announcements. HR Admin operates only assigned modules; Employee has a personal workspace. Assignments are fictional browser-local records, separate from the hosted company-domain login policy. See [role and access rules](docs/ROLE_AND_ACCESS.md).

Added grouped navigation, keyboard quick search (Ctrl/Cmd+K), role-aware attention centre, dashboard announcements, isolated work sessions per preview account and a Build guide with walkthrough, exact permission matrix and implementation map. The guide helps PM/dev teams distinguish reviewable UI from backend work. All source and test fixtures remain reusable and no production company access has been changed.

## Current scope and admin blueprint

Open **Control centre** to review administrative record editing and module settings. HR Admin actions follow delegated module, Configuration and Communications grants. See [scope audit](docs/SCOPE_AUDIT.md), [backend blueprint](docs/ADMIN_BACKEND_BLUEPRINT.md) and [leave/login policy](docs/LEAVE_AND_LOGIN.md). All changes remain fictional and browser-local; the production HR portal is not connected.

## Expense module — integrated version 2

Open **Expenses** in the portal. The shared package supports category-specific short forms, mandatory PDF/image bills with preview, the assigned employee's manager inbox, mandatory HR final approval, locked CAD payouts and the expense-only ledger. Base salaries stay separate. See [Expense module integration](docs/EXPENSE_MODULE.md) for the management click-through and production boundaries. The exact bundled source is hash-verified by the integration tests; the standalone package is maintained in the private bevy-expense-workspace repository. Demo files/claims remain browser-local and Google payroll/payment actions remain simulated.

## Single-date claims and shared approval inbox — 11 November 2026

Every employee has an Approval inbox. Any active colleague may be selected for initial review; HR receives every submission immediately and gives the final decision after that review. No selection goes directly to HR. Self-approval, repeated decisions and the same actor completing both stages are blocked. Employees submit only for their signed-in identity; there is no Expenses account picker.

One expense date is required; no start/end inputs. Category-specific fields remain minimal. Bills are mandatory. Duplicate claim IDs, receipt hashes, invoice references, same-day meals and overlapping subscription coverage are checked, including paid history. Similar spending and policy exceptions need human review.

HR/Super Admin → Payroll sync shows an expense-only mapping, frozen payload preview, selected-batch CSV exports, failure/retry simulation and reconciliation. Mismatched row counts, keys, identity or amounts block payment confirmation. Retries repair the same batch; each paid claim gets one settlement allocation.

The reimbursement subledger balances Approved CAD + locked FX adjustment = Paid CAD + Outstanding CAD. Original-currency balances remain separate. Employees do not enter debit/credit journal lines. This is a reimbursement ledger, not a full accounting system.

Google Sheets remains clearly labelled simulated. Production requires an authenticated server connector, database transactions/unique constraints, receipt storage/scanning and append-only audit records. Give it access only to an expense-only spreadsheet. The salary workbook owner imports only the selected Batch ID and Employee ID reimbursement total; base salaries never enter this portal. Browser tests do not prove production isolation or concurrency safety.

## Three-month fictional payroll replay
Payroll sync → Replay 3-month payroll demo. An isolated instance of the real expense engine simulates September, October and November 2026 for three fictional employees. Steps: Email sync → Calculate payroll → Confirm fictional payment → Check next period. The salary roster exists only in this separate example; normal expense exports contain no base salary. Your workspace claims and connection are unchanged. Fixed fixture FX is illustrative, not a historical market rate.

| Month | Reimbursement CAD (all 3) | Final payroll CAD (all 3) | Example |
|---|---:|---:|---|
| September 2026 | 56.01 | 3,596.01 | Transfer on 8th; 9th expense deferred |
| October 2026 | 67.98 | 3,607.98 | Transfer on 12th; deferred + late-approved claims included once |
| November 2026 | 56.01 | 3,596.01 | Transfer on 10th; prior paid claims excluded |

20 unique expense settlements across 3 months. Draft/unapproved, rejected and company-paid examples stay out. Test buttons demonstrate duplicate import, wrong email and already-processed run blocking. Download all 3 months as a clearly labelled fictional payroll CSV with salary, reimbursement, adjustments, final pay and simulated payment references. These are calculated replay examples, not actual Google Sheets or bank activity.
