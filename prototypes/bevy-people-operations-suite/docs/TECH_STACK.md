# Technology and data inventory

This describes checked-in code, not a promise that all integrations are running. Last reviewed: 23 November 2026.

| Module | Frontend / languages | Backend / server technology | Database or storage now | Deployment/configuration state |
| --- | --- | --- | --- | --- |
| Suite tooling | HTML/CSS launcher; JavaScript `.mjs`; JSON config | Node.js HTTP preview, npm workspaces, Node test runner; GitHub Actions | None | Local loopback preview; CI checks only |
| HR portal | Plain HTML, CSS, JavaScript ES modules | JavaScript Worker access gate and Node build scripts; Python local serving helper | Browser localStorage with fictional seed | Host-specific gated build; company SSO/backend not integrated |
| Expenses | Plain HTML, CSS, JavaScript; `.cjs` tests/tools | No deployed business backend in this repo | Browser-local claim/ledger state; IndexedDB receipt files | Interactive demo + exports; Google write connector not connected |
| Insurance | HTML/CSS/inline JavaScript; local JavaScript validation | Google Apps Script JavaScript/V8 `.gs`; advanced Google Sheets API v4 | Fictional local fixture; optional authorized staging Google Sheet | Latest protected runtime source imported; no deployment performed here |
| Daily updates | Plain HTML/CSS/JavaScript; Supabase client in connected mode | Supabase Auth; PostgreSQL SQL/PLpgSQL functions + RLS | Browser demo by default; optional Supabase PostgreSQL | URL/key blank; isolated PGlite database verification only |

**Not used as the current suite architecture:** React, Next.js, Express business API, MongoDB, MySQL, Redis or a shared production ORM. Do not provision these merely because this is a monorepo.

## Important source files

| Area | Read these paths |
| --- | --- |
| Root commands / dependencies | `package.json`, `package-lock.json`, `.github/workflows/verify.yml` |
| HR fields and calculations | `apps/hr-portal/web/profile-schema.mjs`, `domain.mjs`, `permissions.mjs`, `seed.mjs` |
| HR hosting | `apps/hr-portal/worker/gate.mjs`, `scripts/build.mjs`, `docs/HOSTING_AND_ACCESS.md` |
| Expense transactions and payroll | `apps/expenses/dist/engine.js`, `payroll.js`, `payroll-lab.js`, `receipts.js` |
| Expense implementation / operator guide | `apps/expenses/docs/IMPLEMENTATION.md`, `PAYROLL_RUNBOOK.md` |
| Insurance runtime / access | `apps/insurance/server/adapter.gs`, `apps-script/Code.gs`, `Dashboard.html`, `appsscript.json` |
| Insurance data contract | `apps/insurance/docs/DATA.md`, `OPERATIONS.md` |
| Daily backend | `apps/daily-updates/backend-check.mjs`, `config.js`; optional SQL supplied separately from private source |

## Daily-updates data model

The optional private SQL reference defines `employees`, `leaves`, `holidays`, `updates`, `update_versions`, `work_sessions`, `session_events`, `midday_exceptions`, and `exception_events`. Functions include update submission, work actions, server time and privileged review/role operations; inspect schema for exact signatures. RLS separates employee records from authorized team access. SQL/PLpgSQL is backend logic, not merely a CSV layout.

`@electric-sql/pglite` runs isolated PostgreSQL-compatible checks on a disposable local database. It is a **test dependency**, not the production database. Node 24 is used by CI; the root supports Node >=22. The lockfile pins the dependency graph. Browser code, Node tooling and Apps Script V8 are different execution environments even though all use JavaScript.

## Configuration and confidential information

| Setting | Location | Rule |
| --- | --- | --- |
| Daily Supabase URL / anon key | `apps/daily-updates/config.js` | Use staging project; anon key requires effective RLS; never service-role key |
| Insurance Sheet / script project | `Code.gs` placeholder constant; project mapping excluded | Existing identifiers are not credentials; use a copied staging Sheet and separate script project |
| Insurance optional local source | `apps/insurance/config.js` | Fictional fixture by default; no live feed fetched automatically |
| HR host identity | Worker gate / hosting docs | Configure server-owned identity; do not treat browser account selector as login |
| Payroll | Expense runbook | Expense totals only; confidential salary workbook stays outside portal |

No common `.env` automatically connects these modules. Google OAuth credentials, session cookies and service-role secrets are not part of the intended repository configuration. Insurance snapshots are internal business data and are excluded. The local fixture is explicitly fictional.
