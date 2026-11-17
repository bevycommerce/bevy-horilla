> Current staging guidance: [STAGING_HANDOFF.md](STAGING_HANDOFF.md). Latest stack: [TECH_STACK.md](TECH_STACK.md). Insurance now includes Apps Script/Sheets source; see [merge report](INSURANCE_MERGE.md). The local preview remains disconnected.

# Developer handoff

## Daily work

1. Clone this private repository and run `npm ci --ignore-scripts` with Node 24.
2. Run `npm start` and use the local launcher to select a module.
3. Make changes inside the relevant `apps/` folder.
4. If expense assets change, run `npm run sync:expenses`. If insurance validation changes, run `npm run sync:insurance`.
5. Run `npm run verify` before committing. The same checks run in GitHub Actions.

## Commands

| Command | Purpose |
| --- | --- |
| npm start | Loopback-only launcher for all four modules |
| npm run check | JavaScript syntax and expense-copy consistency |
| npm test | 199 module and integration tests |
| npm run test:database | In-memory daily-updates PostgreSQL checks |
| npm run build | Build the HR access-gated Worker |
| npm run verify | All checks, tests, isolated DB checks and protected build |
| npm run sync:expenses | Refresh the embedded HR expense module |

## Module-specific setup

- **HR:** Original handoff and access-gate documentation remain under `apps/hr-portal/docs`. The original Worker and deployment metadata remain in that app. The local preview bypasses production hosting auth for development; it is not a production server.
- **Expenses:** All executable assets are under `apps/expenses/dist`. Requests require proof and HR/Super Admin validation. Payout logic reserves exact claims and locks FX. Actual Google credentials/writes and durable transaction enforcement are not connected in the demo. Keep salaries in the separate payroll file.
- **Insurance:** See `apps/insurance/README.md`. Source configuration is blank by default. The parser expects the existing masked Share View column contract. An HTML-only private GitHub repository is not an authentication layer for data feeds.
- **Daily updates:** `config.js` contains only public project values and is blank by default. `schema.sql` is the current full schema for a **new** database. The `upgrade_*` files are historical migrations for matching older installations, not a sequence to run after the full current schema. Database tests run in PGlite memory and do not contact Supabase.

## Integration boundary

The four modules share source management and a local launcher. Their production identities and databases remain separate. HR already embeds its expense module through a checked same-origin context handoff. Insurance and standalone daily-updates are available as independent modules; their backend integration into HR is still a future task. Do not interpret a demo role switch as authorization.

For a future hosted suite, protect all module routes at the server and preserve the HR gate's direct-asset checks. Configure independent secrets in the host's secret store, not in this repository. No deployment or production secret change is part of this consolidation.
