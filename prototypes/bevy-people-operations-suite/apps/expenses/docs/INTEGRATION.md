## Payroll v4.1 · saved email connection

Set up payroll company emails once; later choose period → Sync expenses. The shared module normalizes email, retains internal Employee ID, blocks identity mismatches and reuses the same run on retry. CSV column B is now Company Email; column K preserves Employee ID. See PAYROLL_RUNBOOK.md for the current guarded formula. Real Google writes are still simulated.

## Payroll v4 · 12 November 2026

Payroll sync now starts with fixed-cycle/custom/30-day period selection, eligibility preview, separate Late unpaid totals, all-employee frozen runs and payroll-ready summary CSV. CSV import is the working recommended path; automatic Google sheet creation/linking is explicitly a production connection blueprint. See docs/PAYROLL_RUNBOOK.md (or PAYROLL_RUNBOOK.md from this docs directory) for formulas and operation. This supersedes older single-batch-only sync instructions below.

# Shared expense module v3

The standalone dist/ assets are copied unchanged to the main portal web/expenses/ with scripts/sync-module.cjs. The generated manifest records every SHA-256 hash.

Embedded mode receives the current employee, active directory and mapped role through same-origin postMessage. Both sides verify origin and exact parent/iframe source. Employee sees only own expenses. Only HR/Super Admin gets validation, payout, sync and controls. No expense account selector. This context wiring is a prototype, not server authentication.

The main portal retains its company-domain server gate for every asset. Parent module grants determine whether expense administrator tools are available. Browser storage namespaces are separate between standalone and embedded mode. Expanded scenario and empty mode preserve the host directory, and remap fictional owners to host employee accounts.

Production must use server-authoritative immutable Employee IDs, transactional authorization/version checks, private evidence storage and an expense-only Sheets connector. PAYROLL_RUNBOOK.md describes operator steps and connector contracts. Keep the salary workbook separate.
