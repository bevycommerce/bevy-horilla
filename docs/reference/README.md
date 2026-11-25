# Reference

One file per subsystem. Open the one your task needs; do not read the folder.

| File | Covers |
|---|---|
| [`APP_MAP.md`](APP_MAP.md) | **Start here.** Which of the ~45 apps owns what, and the directories that are not apps |
| [`SCREENS.md`](SCREENS.md) | The `horilla_views` cookbook: list, nav, form, detail, filters, the HTMX idioms |
| [`WORKSPACE.md`](WORKSPACE.md) | The Bevy Workspace apps: models, payroll compatibility, Fix My Times, every setting |
| [`API.md`](API.md) | The DRF surface, JWT auth, tenant-scoped authentication, throttles, adding an endpoint |
| [`SCHEDULED_JOBS.md`](SCHEDULED_JOBS.md) | Every registered job and its trigger; the one documented exception |
| [`LOCAL_SETUP.md`](LOCAL_SETUP.md) | Getting it running, first sign-in, environment variables, troubleshooting |
| [`TESTING.md`](TESTING.md) | Running tests, the test kit, the coverage floor, what to test, click-testing, what CI checks and where |
| [`ENVIRONMENTS.md`](ENVIRONMENTS.md) | Branches, how a deploy happens, what staging is today, health endpoints |
| [`PEOPLE_OPERATIONS.md`](PEOPLE_OPERATIONS.md) | The static prototype suite and the constraints on how it is served |

Also in `docs/`, outside this folder:

| File | Covers |
|---|---|
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | The system map |
| [`../DEVELOPER_GUIDE.md`](../DEVELOPER_GUIDE.md) | How to write code here |
| [`../workspace_api.md`](../workspace_api.md) | The Workspace API contract (pre-existing) |
| [`../v1-to-v2.md`](../v1-to-v2.md) | The v1 → v2 cutover record and the production procedure (pre-existing) |

## What belongs here

A reference file describes **how a subsystem works now**. Not why a past change was made, not a
plan, not a checklist.

- A decision to stay consistent with → [`../DECISIONS.md`](../DECISIONS.md)
- Something still open → [`../FOLLOW_UPS.md`](../FOLLOW_UPS.md)
- A rule binding every change → [`../compliance/`](../compliance/README.md)
- A workflow → [`../playbooks/`](../playbooks/README.md)

When a change makes one of these files wrong, fix it in the same PR.

---

> **Didn't find what you came here for?** Log it in [`../navigation/MISSES.md`](../navigation/MISSES.md).
