# Start here — PM, HR and leadership

Reviewed 17 November 2026. This private repository is the central source for four Bevy people-operations modules. It gives the company development team one place to review code, tests, scope and the next implementation steps.

## Current status in simple terms

- HR portal: an interactive prototype for employee profiles, leave, devices, daily work and admin screens. Changes stay in the browser. They are not saved to a shared company database.
- Expenses: a demo where employees submit their own claims and receipts. It includes HR/Super Admin approval, duplicate checks, payroll periods and exports. Real base salaries are kept outside the portal.
- Insurance: includes the latest Google Apps Script frontend, backend and Sheet backup. The existing live system uses Google Workspace and Google Sheets. The local preview does not load live data.
- Daily updates: includes an interactive demo and an optional Supabase backend with SQL, access rules and server-side work timers. That backend is not connected in this suite.

**One repository does not mean one shared login or database.** The HR prototype uses the same expense source as the standalone demo. The company team still needs to connect the other modules in staging. A private GitHub repository protects source access; the deployed website needs its own access controls.

## Where each reader should go

| Reader | Read first | Outcome |
| --- | --- | --- |
| Leadership / HR | This page, [feature map](FEATURE_MATRIX.md) | What can be demonstrated and what remains |
| PM | Feature map, [implementation plan](PRODUCTION_ROADMAP.md) | Assignable work with acceptance conditions |
| Developer | [architecture](ARCHITECTURE.md), [technology inventory](TECH_STACK.md) | Runtime, data ownership and source paths |
| Release owner | [staging handoff](STAGING_HANDOFF.md), [verification](VERIFICATION.md) | Safe source import, environment setup and release evidence |

## A five-minute review

1. Follow the root README to run the local launcher.
2. Open HR and try fictional employee/profile/leave workflows.
3. Open standalone expenses, then HR → Expenses. Both use matching source assets. Each route has separate browser state; shared code is not shared persisted data.
4. Try a receipt, approval and payroll export using fictional data. Do not enter confidential salaries.
5. Open insurance local preview: source is intentionally disconnected. Read its backend and data contract to understand the existing protected Google system.
6. Open daily updates demo and inspect its documented connected-mode setup.

The dated insurance backups contain internal records. Do not attach them to a public demo, public issue, or public static deployment. Live spreadsheets and Apps Script deployments were not changed by this merge.
