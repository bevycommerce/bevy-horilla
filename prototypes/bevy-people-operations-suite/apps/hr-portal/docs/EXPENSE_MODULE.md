## Payroll v4.1

Host context now includes company email with Employee ID. One-time demo mapping is saved; subsequent period sync matches normalized emails and reuses frozen runs. Email changes, duplicates and missing mappings block handoff. See EXPENSE_PAYROLL_RUNBOOK.md.

## Payroll v4 update

Shared assets now include payroll.js. Period preview, atomic multi-employee runs and summary CSV use the same code in both demos. See EXPENSE_PAYROLL_RUNBOOK.md. Automatic Google file creation is simulated; CSV is functional.

# Shared expense module v3

The standalone dist/ assets are copied unchanged to the main portal web/expenses/ with scripts/sync-module.cjs. The generated manifest records every SHA-256 hash.

Embedded mode receives the current employee, active directory and mapped role through same-origin postMessage. Both sides verify origin and exact parent/iframe source. Employee sees only own expenses. Only HR/Super Admin gets validation, payout, sync and controls. No expense account selector. This context wiring is a prototype, not server authentication.

The main portal retains its company-domain server gate for every asset. Parent module grants determine whether expense administrator tools are available. Browser storage namespaces are separate between standalone and embedded mode. Expanded scenario and empty mode preserve the host directory, and remap fictional owners to host employee accounts.

Production must use server-authoritative immutable Employee IDs, transactional authorization/version checks, private evidence storage and an expense-only Sheets connector. PAYROLL_RUNBOOK.md describes operator steps and connector contracts. Keep the salary workbook separate.
