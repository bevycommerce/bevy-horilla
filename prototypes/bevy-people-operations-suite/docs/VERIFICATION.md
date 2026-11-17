# Verification — 17 November 2026

Executed `npm run verify` locally with Node 24.22.1. Result: **PASS**.

| Check group | Result |
| --- | --- |
| HR portal | 33/33 tests passed |
| Expenses | 133/133 tests passed |
| Insurance | 15/15 tests passed |
| Daily updates | 13/13 tests passed |
| Suite HTTP integration | 5/5 tests passed |
| Total automated tests | **199/199 passed** |
| Daily-updates database | Schema, RLS isolation, clock protection, breaks, revisions, exception review, approved leave and anonymous denial passed |
| Protected HR Worker build | Passed |
| Standalone/embedded expense equality | Passed |
| JavaScript checks | Passed; includes insurance inline UI script |

Complete console output: [verification-output.txt](verification-output.txt).

## Fixes and evidence

1. **Insurance invalid dates:** replaced permissive `Date.UTC` rollover with round-trip validation. Tests reject February 30, April 31, unknown months and invalid leap days.
2. **Insurance rejection status:** explicit insurer rejection now wins over pending logic. Inconsistent source details can still retain an issue field, while the claim remains rejected.
3. **Insurance payment chronology:** missing/future insurer receipt, receipt before start, reversed settlement and bank dates do not qualify as completed payments.
4. **Insurance numeric input:** malformed values return missing, not zero; valid zero remains zero.
5. **Expense legacy identity:** fill only absent IDs/emails for the three known fictional fixtures during migration. Existing, blank and changed values remain untouched; unknown employee names are not assigned an email. Two regression cases were added.
6. **Shared expense consistency:** resync repaired engine into HR and updated provenance/version in the manifest. Root check fails on future drift.
7. **Repository integration:** loopback-only preview serves supported static assets; five HTTP integration tests check all modules, embedded paths, traversal/metadata/schema rejection, denied writes and response headers.

## Practical limits

These checks cover imported code and the regression scenarios above. They are not a full production penetration test or a claim of zero defects. The latest internal insurance backup files were imported as private source assets. Tests used fictional fixtures; no live Sheet reads/writes, bank transfer, Google auto-write or production database operation was performed. Original live deployments were not changed. The new launcher is local development tooling, not production authentication. Dependency installation completed with scripts disabled; the package lock is committed for repeatability.

## Latest insurance merge coverage

Five additional server checks cover canonical/server equivalence, exact domain denial, rejected-record redaction, read-only manifest and reproducible generation. HTTP integration additionally denies insurance backups, legacy HTML, live redirect and server files. See [merge report](INSURANCE_MERGE.md).
