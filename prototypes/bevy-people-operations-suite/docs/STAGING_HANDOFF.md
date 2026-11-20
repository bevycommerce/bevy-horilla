# Company staging handoff

## Readiness decision

**Ready for source review and controlled staging integration. Not a unified production-ready HR backend.** Local automated verification is recorded in VERIFICATION.md. No company repository, Google deployment or production database was modified by this handoff. The target company repository/branch and hosting stack have not been supplied.

## 1. Import the source safely

The company developer should create a feature branch in the approved private company repo, review its AGENTS.md and build conventions, and import this suite under an agreed folder or adapt its workspace layout. Preserve the destination's workflows, package manager, lockfile and authentication design; do not replace them wholesale with this root. Use a reviewed PR rather than pushing to the company's protected default branch.

Before copying, decide whether internal insurance backups are allowed in the company repository. They contain actual claim/member data. They are optional for running code; omit `apps/insurance/data` if the destination's data policy excludes business records, and document that omission. Never put backups in public build artifacts. Keep source provenance from source-manifest.json even if backup files are excluded.

## 2. Establish a clean baseline

```sh
node --version
npm ci --ignore-scripts
npm run verify
npm start
```

Use Node 24 to match CI. Open localhost:4173. CI does not deploy anything. Only HR currently produces a protected Worker build; the other modules have separate runtime requirements. Do not upload the whole repository as a static document root.

## 3. Configure isolated environments

| Module | Staging setup | Must remain isolated |
| --- | --- | --- |
| HR | Company-approved SSO/gateway; adapt Worker identity contract and build target | No spoofable identity headers; no real banking/profile demo data |
| Expenses | Initially fictional fixtures; implement authenticated API/storage before shared real use | No real payroll salaries or production Google write credentials |
| Insurance | Copy the Sheet into restricted staging Drive; create separate Apps Script project; update Sheet constant and clasp project mapping | Do not run clasp push against the existing production project; no automatic snapshot restore |
| Daily updates | Separate Supabase project; install schema once, set public URL/anon key and invite test identities | No production DB keys; never expose service-role key; disable public self-signup |

For a **new** daily database use `schema.sql`. Do not then run all historical upgrades on top. For an existing installation identify its schema version, back it up, inspect the specific upgrade chain and rehearse it on a copy. Root `test:database` is disposable verification; it does not migrate a Supabase project.

For Google staging enable Sheets v4 advanced service, retain the read-only scopes, `DOMAIN` access and `USER_DEPLOYING`. The deployer's account must read the copied Sheet. Use a separate protected staging /exec deployment. See insurance OPERATIONS.md for deployment and rollback limitations.

## 4. Required acceptance checks before broader sharing

| Check | Expected evidence |
| --- | --- |
| Build / unit / database checks | `npm run verify` and CI green for the exact reviewed commit |
| Authentication | Company user accepted; outsider, signed-out user and disabled employee denied on page/API/direct assets |
| Employee data privacy | Employee cannot fetch another person's profile, receipts or expenses through API requests |
| Approval policy | HR/Super Admin only; no employee privilege escalation; agreed self-approval rule tested |
| Concurrency | Two approvals/exports/retries cannot allocate or pay one claim twice |
| Payroll | Three fictional periods; late claim and early/late transfer examples; paid run frozen; salary data remains outside portal |
| Insurance | Pending, settled, paid, rejected count-only, impossible dates, missing bank confirmation, refresh and mobile views |
| Daily connected mode | Cross-user RLS, timer server clock, break/resume, EOD, edits/audit and leaver denial |
| Operations | Error reporting without sensitive records; DB/receipt backup restore rehearsal; release owner and rollback recorded |

Unit tests and mocked Google services do not replace real account/deployment checks. Current code verification does not certify these company-environment acceptance checks as completed.

## 5. Release and rollback

Record source commit, environment, schema version, Google script version, deployer and QA evidence in the company PR. Deploy staging first and obtain the company's normal release review. Tag a known-good revision. Keep a database backup before migrations; application rollback alone cannot reverse a destructive schema change. For Google use Manage deployments to promote or roll back a version; editing code or pushing Git does not change an already versioned deployment. Never restore the dated snapshot over live Sheet inputs as part of routine deployment.

## Definition of done for the next company PR

Destination conventions are respected; no real records leak into static artifacts; authentication is enforced server-side; the applicable acceptance checks above have evidence; PM/HR know which modules remain prototypes; and a named release owner can explain and execute rollback.
