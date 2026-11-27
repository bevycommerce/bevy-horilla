# People Operations prototype

A static front-end suite under `prototypes/bevy-people-operations-suite/`, served to signed-in
staging users so HR can review it. **It uses fictional data and is not wired to the HR database.**

## Where it is served

`horilla/people_operations_preview.py`, mounted in `horilla/urls.py`:

| URL | Serves from |
|---|---|
| `/people-ops/` | the suite's index |
| `/hr/…` | `apps/hr-portal/web` |
| `/expenses/…` | `apps/expenses/dist` |
| `/insurance/…` | `apps/insurance` |

`/daily-updates/` is **not** part of this — that is the real `daily_updates` app. The suite page
links to it.

## How the view is constrained

Read `horilla/people_operations_preview.py` before changing anything here. It deliberately mirrors
the prototype's own preview server, and is a hand-written static file server, which is a category of
code that goes wrong:

- `@login_required` — staging sign-in required.
- An extension allowlist (`.html`, `.js`, `.mjs`, `.css`, `.svg`, `.pdf`). Anything else is refused.
- Path rejection for `..`, backslashes, empty segments and dotfiles, then a `resolve()` check that
  the candidate is genuinely under the module's root.
- Tests, SQL and `backend-check.mjs` are never served.
- `insurance` serves exactly three files; `hr` allows one level of `expenses/` nesting and nothing
  deeper.
- Fixed headers on every response: `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: no-referrer`.

Any change that widens what is servable is a security change. Say so in the PR and justify each new
path or extension.

## Its CI

`.github/workflows/bevy-people-operations-prototype.yml` runs Node 24 checks inside
`prototypes/bevy-people-operations-suite/`, on PRs into `staging` or `bevy-hr-portal-dev-2.0` that
touch those paths.

**This is the only workflow that runs on `staging` PRs.** Everything else triggers on `dev/v2.0` and
`2.0` — so a Python change into `staging` has no gate
([`AGENTS.md` — Defaults](../../AGENTS.md#defaults)).

## Working on it

- The suite has its own `package.json`, `tests/`, `scripts/`, `docs/`, `README.md`,
  `PUBLIC_HANDOFF.md` and `source-manifest.json`. Work inside that directory and run its own checks.
- Do not wire it to the HR database as a side effect of another task. Turning a prototype page into
  a real feature is a [feature](../playbooks/feature.md) built on `horilla_views`, in the owning
  Django app — not a static page given a data source
  ([`compliance/screens-use-horilla-views.md`](../compliance/screens-use-horilla-views.md)).
- Do not let prototype assets grow into the Django `static/` tree.
- It is the only SPA-shaped thing in this repository, and deliberately separate. Do not take it as
  precedent for building HR screens.
