# Insurance — code-only staging reference

This public handoff contains the dashboard UI, Apps Script backend adapter, canonical validation logic and fictional test cases. Internal claim records, snapshots, live redirects, project mappings and legacy pages are excluded.

The local preview is disconnected. `server/adapter.gs` uses a placeholder Sheet ID. Configure a separate, restricted staging Sheet before intentional deployment. Keep domain-only access and read-only Sheets scopes. Do not deploy this folder as a public data feed.

Edit calculations in `logic.js` and the Google service adapter in `server/adapter.gs`; run `npm run sync:insurance` from the suite root. Generated `apps-script/Code.gs` combines both. Run `npm run verify` before review.

See [data contract](docs/DATA.md), [operations](docs/OPERATIONS.md) and [public handoff](../../PUBLIC_HANDOFF.md). No deployment runs automatically.
