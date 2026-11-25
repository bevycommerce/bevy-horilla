# API

DRF, mounted from `horilla_api/apps.py::ready()` at **`/api/v1/`**, with **`/api/`** kept as an alias.

`/api/` is deprecated. It is kept rather than redirected because existing clients already use it —
removing it would be exactly the breaking change the versioning was introduced to prevent. New
integrations use `/api/v1/`; `/api/` goes away in a major release.

## Clients

| Client | Uses |
|---|---|
| Horilla mobile app | `/api/v1/<app>/…` plus the screen-shaped aggregates under `/api/v1/mobile/` |
| BevyLoop desktop companion (separate repository) | `/api/v1/workspace/v1/…` — see [`../workspace_api.md`](../workspace_api.md) |

A response-shape change is a breaking change for a shipped client. Add a field; do not rename or
remove one without a version note in the PR.

## Authentication

SimpleJWT:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/login/` | Obtain access + refresh. Throttled under the `login` scope |
| `POST /api/v1/auth/refresh/` | Rotate. Rotation blacklists the superseded token |
| `POST /api/v1/auth/logout/` | Blacklist the refresh token |

Access token 60 minutes, refresh 30 days, rotation with `BLACKLIST_AFTER_ROTATION`, and a password
change revokes tokens. `rest_framework_simplejwt.token_blacklist` is installed for this: without it
a refresh token stays valid for its full lifetime after logout, and rotation silently leaves every
superseded token usable.

**The authentication class is `horilla_api.authentication.TenantScopedJWTAuthentication`**, not
DRF's default. It subclasses `JWTAuthentication` to also set the company ContextVar that
`HorillaCompanyManager` scopes on. `CompanyMiddleware` cannot do it for API calls: middleware runs
before DRF resolves the token, so it sees `AnonymousUser` and returns early, leaving queries
unscoped. Any new authentication class must do the same —
[`compliance/company-scoping.md`](../compliance/company-scoping.md).

## Defaults

From `REST_FRAMEWORK` in `horilla/settings/base.py`:

- `IsAuthenticated` on everything by default.
- `PageNumberPagination`, `PAGE_SIZE` 20. Keep endpoints paginated
  ([`compliance/bounded-data-access.md`](../compliance/bounded-data-access.md)).
- `DjangoFilterBackend` for filtering.
- Throttling: `AnonRateThrottle`, `UserRateThrottle`, `ScopedRateThrottle`. `django-axes` already
  locks an account after repeated bad passwords, but it counts *failures* only — a caller could
  hammer the login endpoint with valid credentials, or any authenticated endpoint at any rate,
  without tripping it. These throttles bound that. Do not remove a scope to make a client work;
  raise the rate deliberately and say why.

## Surfaces

`horilla_api/urls.py` mounts one module per app under `horilla_api/api_urls/<app>/`:

`auth`, `asset`, `base`, `employee`, `notifications`, `payroll`, `attendance`, `leave`, `helpdesk`,
`project`, `onboarding`, `offboarding`, `recruitment`, `pms`, and `mobile` (aggregates).

Bevy's Workspace API is mounted alongside them:

| Path | App |
|---|---|
| `/api/v1/workspace/v1/updates/` | `daily_updates.api.urls` |
| `/api/v1/workspace/v1/reminders/` | `workspace_reminders.api_urls` |
| `/api/v1/workspace/v1/` | `workspace_attendance.api.urls` |

Pre-existing attendance endpoints built for the mobile app: `/api/v1/attendance/clock-in/`,
`/api/v1/attendance/clock-out/`, `/api/v1/mobile/home/`.

**Every mutating Workspace call requires an `Idempotency-Key` header**, and a repeat replays the
stored response ([`WORKSPACE.md`](WORKSPACE.md)).

## Documentation

`drf-yasg` generates the schema. Swagger at `/api/v1/swagger/`, ReDoc at `/api/v1/redoc/`, raw
schema at `/api/v1/swagger.json`.

They are **public only when `DEBUG`** and admin-only otherwise (`IsAdminUser`), so do not link a
colleague to staging's Swagger expecting it to open. The schema is tagged per module by
`horilla_api.schema.ModuleTaggingAutoSchema` and ordered by `OrderedTagSchemaGenerator`; tag order is
the order in the generated spec.

## Adding an endpoint

1. Serializer and view in the owning app's `api/` package, or under
   `horilla_api/api_urls/<app>/`.
2. Permission class — `IsAuthenticated` is the floor, not the answer. An HR-only endpoint needs the
   Django permission too ([`compliance/access-control.md`](../compliance/access-control.md)).
3. Paginated, with a stated maximum page size if you override the default.
4. Company-scoped reads go through the model's `HorillaCompanyManager`; do not re-implement scoping
   in the view.
5. Route it from `horilla_api/urls.py`, under `/api/v1/`.
6. Add the row to the table above and, for a Workspace endpoint, to
   [`../workspace_api.md`](../workspace_api.md).
7. Check the generated Swagger renders it, and that an unauthenticated call is refused.
