# Insurance public handoff

The current Apps Script frontend/backend and strict date, amount and payment-order validation are included. Private Sheet backups, real claim rows, live URLs, deployment IDs and historical pages are excluded. Local tests use fictional fixtures; no production deployment is made.

Canonical sources are `apps/insurance/logic.js` and `apps/insurance/server/adapter.gs`. Run `npm run sync:insurance` after edits. The generated backend keeps domain checks, read-only Sheets access and rejected-record redaction. Configure only a separate staging Sheet before runtime testing.
