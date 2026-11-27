# Company scoping

Records belong to a `Company`. `base/horilla_company_manager.py::HorillaCompanyManager` filters
querysets to the company in the request context, which `base.middleware.CompanyMiddleware` sets.

The failure mode is silent and serious: a model that *looks* scoped but reads through a plain
manager returns every company's rows, so one company's staff see another's employees, salaries or
leave.

`HorillaModel` sets `objects = models.Manager()`. **Scoping is opt-in.** A new model gets nothing
for free.

How-to: [`DEVELOPER_GUIDE` — Company scoping](../DEVELOPER_GUIDE.md#company-scoping).
Context: [`ARCHITECTURE` §4](../ARCHITECTURE.md#4-multi-company-tenancy).

## Do

- Give a model that holds per-company data a `HorillaCompanyManager` with the `related_company_field`
  path that reaches `Company` from it.
- Run `python manage.py check --fail-level WARNING --tag horilla.tenancy` before the PR
  (`base/checks.py`). It warns about models that look company-scoped and are not.
- In an API view or any code path that is not a browser request, make sure the company context is
  set. DRF resolves the token *after* middleware, so `CompanyMiddleware` sees `AnonymousUser` and
  returns early — `horilla_api.authentication.TenantScopedJWTAuthentication` is what sets it. A new
  authentication class must do the same.
- Scope a filter's option list per request. `HorillaFilterSet.ajax_fields` calls `queryset_fn(request)`
  on every request precisely so it can.
- Test the boundary with `horilla/testkit/company.py::CompanyFilterTestMixin`: set the company
  context, assert the other company's rows are absent.

## Do not

- Read a company-scoped model through `Model.objects.all()` in a view, an export, a report, a
  scheduled job or a serializer when the result reaches a user.
- Bypass the manager with `_base_manager`, `objects.db_manager`, or raw SQL to "make the query
  simpler".
- Mutate `model.company_filter` or other class attributes in a test to fake scoping — current Horilla
  tenancy reads `get_selected_company()`, not the class attribute, so the test proves nothing.
- Add a cross-company report without saying in the PR who may see it and which permission gates it.
