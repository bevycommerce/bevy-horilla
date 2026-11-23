# Company staging handoff

## Readiness decision

**Ready for source review and controlled staging integration. Not a unified production-ready HR backend.** Local automated verification is recorded in VERIFICATION.md. No company repository, Google deployment or production database was modified by this handoff. The target company repository/branch and hosting stack have not been supplied.

## 1. Import the source safely

The company developer should create a feature branch in the approved private company repo, review its AGENTS.md and build conventions, and import this suite under an agreed folder or adapt its workspace layout. Preserve the destination's workflows, package manager, lockfile and authentication design; do not replace them wholesale with this root. Use a reviewed PR rather than pushing to the company's protected default branch.

Internal insurance backups and live identifiers are excluded from this company handoff. Do not copy them into this public Git network. Keep staging fixtures fictional or explicitly approved and redacted. source-manifest.json records import provenance, not current file integrity after review fixes.

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
| Insurance | Create an approved fictional/redacted Sheet in restricted staging Drive; never copy live claim data for a demo; create separate Apps Script project; update Sheet constant and clasp project mapping | Do not run clasp push against the existing production project; no automatic snapshot restore |
| Daily updates | Separate Supabase project; install schema once, set public URL/anon key and invite test identities | No production DB keys; never expose service-role key; disable public self-signup |

Daily SQL installers are excluded from the company repository. The optional private standalone reference and its v1→v6 upgrade chain are documented in Daily Updates README. Set BEVY_DAILY_SQL_DIR only for disposable local verification. Company database changes require a separate Django implementation and migrations.

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

## Review fixes — 23 November 2026

- Latest `staging` is the starting point. The proposal remains one People Operations preview feature; real application payroll, database models, login and deployment configuration are unchanged.
- Slash routes serve their index instead of redirecting forever. Signed-out page and direct-asset access is tested through the Django decorator.
- Managers see only their own Daily Updates; HR Admin/Super Admin keep authorized workspace review. The optional standalone reference uses `hr` for that privileged policy.
- Exception review rejects stale revisions. EOD availability uses elapsed wall time since the latest EOD edit, independently of eight net hours. Existing sessions can be corrected after a late leave approval.
- Cross-tab refresh invalidates open editors and rebinds the current employee session. Uploads recheck the current claim/account before replacing anything. FX responses are validated completely before replacing the quote.
- Claims retain an employee ID. Missing legacy ownership requires explicit HR verification and reapproval; name reuse cannot move an approved claim into another person's payroll.
- Both expense copies match byte-for-byte. The two payroll runbooks match and block duplicate current payroll rows, duplicate/conflicting imports, completed runs and wildcard email matches.
- Insurance staging is fictional. Completed amounts still require valid insurer and bank milestones; overdue rejection and invalid durations are handled consistently. Preset refresh updates dates without discarding custom filters or pagination.
- SQL installers are excluded from the company tree under CLAUDE.md; the reviewed private standalone reference includes a v6 upgrade and disposable upgrade verification. No company database migration is performed.

### Click-test before staging acceptance

1. Sign out of Django and request `/hr/seed.mjs`: expect the login redirect. Sign in, open `/people-ops/`, then open all four modules. `/hr/` must load directly.
2. Switch fictional employee/HR/Super Admin accounts. Employees/managers must have their own Daily Updates only; authorized admins get team review.
3. Keep an HR editor open in one tab and change the workspace in another. The old editor must close. Keep an employee Daily Updates draft focused while another account updates: it must remain attached to that employee.
4. Submit an expense with a fictional bill, approve it as HR, preview a period, sync, export, retry and confirm fictional payment. Paid/reserved claims must stay excluded from a fresh run. Replay the three-month example.
5. In a test copy of a salary workbook, follow PAYROLL_RUNBOOK: test duplicate current rows, a READY plus non-READY duplicate import, an address containing a wildcard, and a previously paid run. Each must block instead of producing a payable amount.
6. Open insurance, confirm the fictional label and counts, then check preset/custom filters, pagination, mobile layout and refresh.

Company CI, signed-in staging checks, real Google authorization and any future backend integration remain release-owner acceptance steps. A successful local prototype build does not certify a production rollout.
