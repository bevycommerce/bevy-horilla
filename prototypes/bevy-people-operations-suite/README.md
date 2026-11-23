# Public-safe company handoff

Read [PUBLIC_HANDOFF.md](PUBLIC_HANDOFF.md) first. Private insurance backups and live configuration are excluded. This folder is a prototype reference served behind staging Django login, not a production HR database integration.

# Bevy People Operations Suite

Private consolidated source for Bevy Commerce HR portal, employee expenses, insurance reporting and daily updates. Reviewed on **17 November 2026**.

| Module | Location | Local preview |
| --- | --- | --- |
| HR portal | `apps/hr-portal` | `/hr/` |
| Expense workspace | `apps/expenses` | `/expenses/` |
| Insurance dashboard | `apps/insurance` | `/insurance/` |
| Daily updates | `apps/daily-updates` | `/daily-updates/` |

## Review and staging handoff

Start with the [plain-language overview](docs/START_HERE.md). Then use the [architecture](docs/ARCHITECTURE.md), [technology/database inventory](docs/TECH_STACK.md), [feature/status map](docs/FEATURE_MATRIX.md), [company staging guide](docs/STAGING_HANDOFF.md), and [implementation plan](docs/PRODUCTION_ROADMAP.md).

Latest insurance source is included without internal dated backups; see the [merge report](docs/INSURANCE_MERGE.md). The company copy is sanitized for its destination repository; keep original business backups private. **Source handoff is ready for review; shared production authentication, persistence and Google payroll writes remain implementation work.** Live systems were not redeployed.

## Start here

Use Node.js 24 (Node 22 or later supported).

```sh
npm ci --ignore-scripts
npm run verify
npm start
```

Open **http://127.0.0.1:4173** to choose a module. `npm start -- --port 4180` changes the local port.

`npm run verify` checks JavaScript, checks the shared expense copy, runs module and cross-tab regression tests, runs optional isolated daily-update database checks when BEVY_DAILY_SQL_DIR is supplied, and builds the protected HR Worker. No live database or Google Sheet is changed. The launcher listens only on loopback and does not publish a website.

## One canonical expense module

Edit `apps/expenses/dist`. Then run:

```sh
npm run sync:expenses
npm run verify
```

The sync command copies the same expense assets into `apps/hr-portal/web/expenses` and refreshes its hash manifest. Verification fails if the standalone and embedded modules drift apart. Source code lives in `dist` because that is the original expense repository structure; do not delete it as a build artifact.

## What was fixed

- Insurance date parsing now rejects impossible dates rather than rolling them into another month.
- Rejected insurance claims retain their rejected state. Missing, reversed or future receipt milestones cannot appear as completed payments.
- Blank and malformed insurance amounts remain missing instead of silently becoming zero.
- Older fictional expense workspaces recover missing demo identity fields for known fictional employees. Existing addresses are preserved; unknown people are never assigned guessed emails.
- Insurance source configuration is explicit and disconnected by default. Opening a development preview does not automatically fetch the old published claim feed.
- One command verifies all modules, with a private-repository CI workflow and no automatic public deployment.

See [verification results](docs/VERIFICATION.md), [developer handoff](docs/DEVELOPER_HANDOFF.md) and [consolidation notes](docs/CONSOLIDATION.md).

## Boundaries

This is a **single source repository containing four runnable modules**, not a claim that their production backends, databases or login systems have been merged. HR/expense demos retain browser-local state; daily updates has its own optional Supabase configuration and SQL schema. Insurance now includes the existing protected Apps Script/Google Sheets backend; its local preview stays disconnected. Production authentication, receipt storage and portal-to-Google writes still need their respective backend integrations. Base salaries stay outside the expense portal.

Existing sites and their access lists are unchanged. Original repositories remain available with their commit history. The imported source commits and every original file hash are recorded in [source-manifest.json](source-manifest.json). Module documentation below each app is retained for context; the root handoff and verification report describe the consolidated version.
