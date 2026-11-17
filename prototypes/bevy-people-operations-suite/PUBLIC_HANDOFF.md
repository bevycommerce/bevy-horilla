# Isolated prototype handoff

## Purpose and safety boundary

This is a public-safe, code-only reference for PM, HR and developer review. It is kept entirely under `prototypes/bevy-people-operations-suite/`. A new, uniquely named root workflow verifies only this folder. Existing application files, Django settings/routes/models, database migrations, requirements, Docker files and workflows are not edited.

The prototype is not registered as a Horilla app. Opening this PR does not connect it to company login, modify a database or deploy a website. Existing company features continue to use their own implementation. Treat this folder as a reference until a separate integration PR is reviewed.

## Run and verify

From the company repository root:

```sh
cd prototypes/bevy-people-operations-suite
npm ci --ignore-scripts
npm run verify
npm start
```

Use Node 24. The preview binds to localhost:4173. Test data is fictional. Daily Supabase configuration is blank; insurance uses a placeholder Sheet ID; hosting metadata is unconfigured. The Worker build verifies packaging but does not establish company SSO.

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

This PR adds files only. Reverting its commit removes the isolated prototype and its new scoped verification workflow. No database rollback is needed because there are no migrations or runtime connections in this handoff. Do not merge or deploy automatically.
