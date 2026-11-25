# Access control

Every screen and endpoint in an HR system is an access decision: salary, contracts, performance
reviews, resignations and candidate records all sit behind one. The server check is the control; the
screen only reflects it.

How-to and the decorator table:
[`DEVELOPER_GUIDE` — Permissions and decorators](../DEVELOPER_GUIDE.md#permissions-and-decorators).

## Do

- Put the check on the view, with Horilla's decorators: `login_required` (Horilla's, not Django's),
  `permission_required`, `any_permission_required`, `manager_can_enter`, `owner_can_enter`,
  `superuser_required`, `delete_permission`, `duplicate_permission`.
- On a class-based view, `@method_decorator(login_required, name="dispatch")`; on a
  `HorillaFormView`, `AddOrChangePermissionMixin` with `add_perm` and `change_perm`.
- Guard an HTMX fragment route with `hx_request_required` as well as its permission — a fragment URL
  is directly reachable.
- **Put a view permission on a list or detail screen.** The `horilla_views` generics do not check one:
  `HorillaListView` gates only the bulk-update and import controls, not `dispatch` or `get_queryset`.
  `login_required` alone means any signed-in employee can read the rows by requesting the list URL.
  Stack `permission_required("<app>.view_<model>")`, or scope `get_queryset()` to the viewer when the
  screen is deliberately "my own records".
- Build permission-dependent toolbar entries inside `__init__`, behind `request.user.has_perm(...)`.
  The class body runs once at import time and has no request.
- Hide or disable a control the user may not use, and say why when it is disabled. A clickable
  control that fails server-side is a bug report waiting to happen.
- Gate a sidebar entry with its `accessibility` callable rather than rendering a link that 403s.
- Scope "my own" and "my team" views by the actual relationship (`owner_can_enter`,
  `manager_can_enter`), not by a filter the user could change in the URL.
- Add a test for a new access rule: the permitted role sees it, the adjacent role does not.

## Do not

- Rely on a template `{% if %}`, a hidden field, a disabled attribute, or the absence of a link as
  the only protection.
- Take an employee id, company id or record id from the request and read it without checking the
  caller may see it.
- Add a new permission string without wiring it into the groups or roles that should have it, and
  saying so in the PR.
- Widen an existing check to make a new screen work. Add the narrower one the new screen needs.
- Use `superuser_required` because the right permission is unclear — find it, or ask.
- Weaken `horilla/decorators.py` or `accessibility/`; they are
  [protected paths](protected-paths.md).
