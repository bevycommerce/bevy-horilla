# People Operations prototype handoff

## Purpose and safety boundary

This is a public-safe, code-only reference for PM, HR and developer review. It is kept entirely under `prototypes/bevy-people-operations-suite/`. A new, uniquely named root workflow verifies only this folder. The only existing application change is URL routing to a new authenticated static preview handler. Existing business models, migrations, settings, requirements and deployment files are unchanged.

The prototype is not registered as a Horilla app. The staging preview requires the existing Django login, including direct asset requests. This gates access to fictional review pages; it does not connect prototype account selectors to real employee permissions or a shared database. Opening the PR does not deploy it. Existing company features continue to use their own implementation. Treat this folder as a reference until a separate integration PR is reviewed.

## Run and verify

From the company repository root:

```sh
cd prototypes/bevy-people-operations-suite
npm ci --ignore-scripts
npm run verify
npm start
```

Use Node 24. The preview binds to localhost:4173. Test data is fictional. Daily Supabase configuration is blank; local insurance uses fictional config data and its server adapter uses a placeholder Sheet ID; hosting metadata is unconfigured. The Worker build verifies packaging but does not establish company SSO.

## Optional database verification

Company repository rules prohibit SQL installers. Daily Updates SQL stays in the private source handoff; it is not a Django migration or a company database integration. For the optional isolated check set `BEVY_DAILY_SQL_DIR` to the reviewed private SQL directory and run `npm run test:database`. `npm run verify` clearly skips this optional check when fixtures are unavailable. Production changes require a separate Django implementation and migrations.

## Excluded from the public copy

- Actual insurance claim CSVs and workbook snapshots.
- Live Sheet, document, Apps Script editor/deployment and portal links.
- Existing Google project mappings and hosting project IDs.
- Legacy insurance pages and archived server copies.
- Demo screenshot binaries and private repository history.

Only sanitized files are added on top of the company branch. Private source history is not merged into this public Git network. The original private suite remains unchanged.

## Review in order

1. [Simple overview](docs/START_HERE.md).
2. [Architecture](docs/ARCHITECTURE.md) and [technology inventory](docs/TECH_STACK.md).
3. [Feature map](docs/FEATURE_MATRIX.md).
4. [Staging handoff](docs/STAGING_HANDOFF.md) and [implementation plan](docs/PRODUCTION_ROADMAP.md).

Those documents also describe the original modules. For this public copy, exclusions and placeholder settings on this page take precedence. No internal backups are included, even where historical notes discuss private backup arrangements.

## Future integration into Horilla

Use the existing Django employee identity, roles, models, services and migration conventions. Reuse reviewed business rules from this reference; do not insert a second production login or database without an explicit architecture decision. Implement one feature at a time in a separate PR with authorization, transaction and integration tests. Keep payroll salaries outside the expense prototype. Adapt the existing company expense and daily-update modules instead of replacing them wholesale.

## Rollback

Reverting the feature removes the prototype, its preview handler, the two preview URL registrations and the scoped verification workflow. No database rollback is needed because there are no migrations or runtime connections in this handoff. Do not merge or deploy automatically.
