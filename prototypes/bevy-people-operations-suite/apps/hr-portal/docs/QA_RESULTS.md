## Current review · 11 November 2026

See PORTAL_REVIEW_2026-11-11.md for the full current section map. Expense scope section 12 is implemented as a shared browser-local module: HR / Super Admin validation only; no manager/employee approval. The Build guide, permissions summary and payroll handoff now reflect this. See EXPENSE_MODULE.md and EXPENSE_PAYROLL_RUNBOOK.md. Older dated notes below remain historical; production integrations are still pending.

# Verification — 5 November 2026

## Automated checks

- Syntax checks passed for frontend modules and server gate.
- 10 meaningful tests passed: workday boundaries, completed-month experience, 30-day archive threshold, valid bank-confirmed claim selection, leap-month ranges, net time/break calculation, assignment invariants, seeded scenarios, exact-domain identity policy, and direct protected asset routes.
- Protected Worker build completed; deployed output contains only server/index.js and hosting metadata, with all frontend assets embedded behind the gate.

## Browser checks completed

- Desktop layout and live hosted dashboard loaded with the owner's signed-in company account.
- Employee name search returned the expected fictional employee.
- Assigning available serial DEMO-SN-00025 from a profile linked it into Assigned assets.
- Insurance 25-row selection, member search 4101, claim timeline and working-day values inspected.
- Employee role preview, EOD submission, 8-hour scenario and sign-out exception flow inspected. Missing Mid-Day was flagged separately; a reason was retained.
- Archives showed disabled deletion before 30 days and available decisions afterward.
- 390px viewport: navigation and insurance layout checked; document width did not exceed viewport; ten claim cards were present.
- Anonymous cloud-browser visit to the hosted root showed the company sign-in screen, not the app.
- Anonymous cloud-browser visit directly to /seed.mjs showed the same sign-in screen, not fixture code.
- Private GitHub visibility verified through GitHub UI and connector metadata; source readback confirmed.

## Verification limits

A real second company reviewer and an actually signed-in outsider account were not available in this session. Exact-domain allow/deny behavior was unit tested. Command-line anonymous and forged-header requests were denied by the hosting edge (403), so those requests do not independently prove application-level header sanitization; the gate relies on the supported Sites authentication ingress. This is a dummy-data review prototype, not a penetration-tested production HR system.

Browser changes are local to the testing browser. New reviewers start with the original fixtures. No live employee records, real insurer data or production portal changes were made.

## Follow-up revision — Daily Updates included now

- Reused Bevy SVG from `bevy-daily-updates-source/bevy-logo.svg` and matched the reference's teal palette.
- Removed the Daily Updates Future label; streamlined dashboard around a workday timer and essential HR summaries.
- 12 tests now pass, including portal-entry auto start, same-day refresh/re-entry, paused draft preservation, closed-day protection and overnight-session retention.
- Browser: reset fictional data, entered portal, observed the working clock already counting without a start button.
- Browser: selected Prayer Break with a note, refreshed, returned to Daily Updates; working time stayed at 00:00:17 while break/elapsed time advanced and draft text remained.
- Browser: resumed, posted inline Mid-Day with multiple evidence links, opened the posted record and verified clickable evidence, next priorities and revision panel.
- Reference-style inline composer, daily activity thread, summary, history and reports are included in the current demo; production portal backend integration remains separate.

## Administrative polish revision

- 17 automated tests pass, including delegated HR permissions, Employee isolation, active account checks, Super Admin-only assignment, self-demotion/suspension guards, confidential-field dependencies and downgrade cleanup.
- Browser: Super Admin assigned Meera Ahmed an HR Admin role with Assets and Confidential details disabled. Preview showed neither Assets navigation nor confidential profile tab. Access management and Portal settings were absent from HR Admin navigation.
- Global and module actions use the same sample policy; permissions remain a browser simulation and the hosted company-domain boundary is unchanged.
- Each preview persona now keeps its own workday/draft container. Current source includes the new role/access handoff and an updated PM/dev Build guide.

- Browser: Employee quick-search for assets returned no administrative page. Super Admin posted a sample announcement and verified it appeared on the dashboard.

## Scope audit and administration revision

- 29 automated tests pass, covering all 24 stored profile fields and eight departments, profile validation, long Member ID masking, leave/weekend reminder suppression, device edit lifecycle preservation, claim correction constraints, time correction history and separate administrative grants in addition to existing tests.
- Browser: profile editor shows all four groups and full field list; fictional education change saved and appeared in Overview.
- Browser: Control centre shows permitted record/settings actions across six modules plus announcement/template editing; branded email/in-app previews rendered.
- Browser: inventory name correction saved while Assigned state, employee, serial and assignment date stayed linked.
- Production HR database, insurer source sync, durable multi-user writes and actual email delivery remain outside this prototype; see the detailed backend integration map.
- Browser: Super Admin granted Configuration and Communications to an existing limited HR Admin. HR preview showed Assets disabled, no Access management/Portal settings, and enabled leave/module/communication editing. HR saved a module policy note successfully.
- Browser: Build guide renders the scope matrix and expandable section 3/4 field checklist; no longer just an unused source constant.
