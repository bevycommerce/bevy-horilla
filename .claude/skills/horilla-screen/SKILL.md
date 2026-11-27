---
name: horilla-screen
description: Build or change an HR screen in the bevy-horilla Django app — a table, its toolbar, a create/edit modal, a detail modal, filters, or the sidebar entry that reaches it. Use whenever a task adds or changes a page people click in this repo, including "add a column", "add a filter", "add a create button", "make this list sortable", or "add a new settings page". Covers the horilla_views generic class-based views, the HTMX composition, where permission checks go, and the checklist a screen must pass.
---

# Building an HR screen

Screens in this app are **not** hand-written pages. They are composed from the generic class-based
views in `horilla_views/generic/cbv/views.py` and assembled in the browser by HTMX. A hand-rolled
page loses saved filters, column toggling, sorting, pagination, bulk actions, export, the history
sidebar, the modal plumbing and the theme — all of which the generics give you for free.

Rule: `docs/compliance/screens-use-horilla-views.md`.
Full cookbook, with every class attribute: `docs/reference/SCREENS.md`.

## Step 1 — read the worked example

Before writing anything, read **`base/cbv/holidays.py`** and its routes in `base/urls.py` (search
for `holiday-`). It is the smallest complete screen in the tree: list, nav, form, detail, export.
Everything below is visible in it.

Then read the app you are working in: an app that already has `cbv/` modules has a local convention,
and matching it matters more than matching this skill.

## Step 2 — locate and plan

1. Find the owning app in `docs/reference/APP_MAP.md`. A new screen almost always belongs in an
   existing app; a new app needs `docs/playbooks/new-app.md` and a reason.
2. Decide the **access rule first**: who may see it, who may change it, and which existing Django
   permission covers it. Everything else follows from that.
3. Decide whether the data is company-scoped (`docs/compliance/company-scoping.md`).
4. Say in chat which routes you will add, the permission on each, and whether there is a migration.
   Wait for approval before coding.

## Step 3 — the routes

A screen is several routes, not one view:

| Route | Class | Renders |
|---|---|---|
| `…/view/` | plain `TemplateView` | the page shell |
| `…/navbar/` | `HorillaNavView` | title, search, create button, filter panel, actions |
| `…/filter/` | `HorillaListView` | the table — **and** the search/filter endpoint |
| `…/creation/`, `…/update/<pk>/` | `HorillaFormView` | the create / edit modal |
| `…/detail-view/<pk>/` | `HorillaDetailedView` | the detail modal |
| `…/export/` | plain `TemplateView` | the export column picker |

The list view's URL is also the search endpoint: `search_url` on both the list and the nav view
points at it, and the nav view's `search_swap_target` names the container to swap.

Add them to `<app>/urls.py`. If the app mounts its own routes, that happens in `<app>/apps.py`'s
`ready()` — most apps here do, which is why a route may not appear in `horilla/urls.py`.

## Step 4 — the classes

```python
@method_decorator(login_required, name="dispatch")
@method_decorator(permission_required("myapp.view_shiftswaprequest"), name="dispatch")
class SwapListView(HorillaListView):
    model = ShiftSwapRequest
    filter_class = SwapFilter
    columns = [(_("Employee"), "employee_id"), (_("Date"), "requested_on")]
    sortby_mapping = [(_("Date"), "requested_on")]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = reverse("swap-list")
        self.view_id = "swapList"
        if self.request.user.has_perm("myapp.change_shiftswaprequest"):
            self.action_method = "swap_actions"
```

**`HorillaListView` does not gate the read.** It checks permissions only for the bulk-update and
import *controls* (`bulk_update_accessibility`, `import_accessibility`); there is no permission check
in `dispatch` or `get_queryset`. So `login_required` alone means **any signed-in employee can read
the list**, including by hitting the list URL directly — it is a fragment route, so there is no page
shell to hide behind. Gate it with `permission_required` as above, the way `asset/cbv/asset.py`
does, or scope `get_queryset()` to the viewer when the screen is deliberately "my own records".

`base/cbv/holidays.py` — the worked example — has no view-permission decorator, because public
holidays are not restricted. Do not copy that part for anything holding employee data.

The rules that are easy to get wrong:

- **Anything that depends on `self.request` goes in `__init__`, not the class body.** The class body
  is evaluated once at import time and there is no request there. This is the single most common
  mistake: a permission-gated create button or action built in the class body either never appears
  or appears for everyone.
- `columns` entries are `(translated label, field or model method)`. A model method that returns
  HTML renders as HTML — that is how per-row action buttons and status pills work.
- `HorillaFormView` serves create and edit from one class; the presence of `pk` decides which.
  `form_valid` returns **`self.HttpResponse()`** to close the modal and reload the list. Returning a
  redirect breaks the HTMX flow.
- Use `AddOrChangePermissionMixin` with `add_perm` and `change_perm` rather than hand-rolled checks.
- `restrict_company_field = False` when the form's company field may legitimately be blank, meaning
  "all companies" — otherwise the base view forces it to the session company.
- Forms subclass `base.forms.ModelForm` / `Form`, not Django's. Filters subclass
  `horilla.filters.HorillaFilterSet`.
- A filter FK or M2M with hundreds of options gets `ajax_fields` on the **filter class** — one dict
  entry, no new view or URL. The docstring on `HorillaFilterSet` in `horilla/filters.py` is the
  spec, and its per-request `queryset_fn` is where company or subordinate scoping goes.

## Step 5 — reach it from the sidebar

```python
# <app>/sidebar.py
MENU = _("Shift Swaps")
IMG_SRC = "images/ui/attendance.svg"
SUBMENUS = [
    {
        "menu": _("My Requests"),
        "redirect": reverse_lazy("swap-home"),
        "accessibility": "myapp.sidebar.my_requests_accessibility",
        "match_prefixes": ["/myapp/swap-requests/detail/"],
    },
]
```

- `accessibility` is a dotted path to a per-request callable. Use it instead of showing a link that
  403s.
- `match_prefixes` exists because active-link highlighting is **path-based**. A sibling URL that is
  not a sub-path of `redirect` needs its prefix listed, or the wrong item highlights — or two do.

## Step 6 — the HTMX idioms

| Intent | Attributes |
|---|---|
| Open a modal | `hx-get="<url>" hx-target="#genericModalBody" data-target="#genericModal" data-toggle="oh-modal-toggle"` |
| Refresh the list | swap the container named by `search_swap_target` |
| Guard a fragment route | `@method_decorator(hx_request_required, name="dispatch")` |
| Re-render messages | target the `ReloadMessages` view |

Write no JavaScript that fetches JSON and renders rows. Swap server-rendered HTML.

## Step 7 — the checklist

- [ ] Routes for shell, nav, list, form, detail — each named, each decorated
- [ ] **A view permission on the list and detail views**, not just `login_required` — the generics do
      not gate the read. Or a `get_queryset()` scoped to the viewer for an "my own records" screen
- [ ] Permission on **every** view; the screen hides or disables what the user may not use, with its
      reason when disabled
- [ ] Fragment routes guarded with `hx_request_required`
- [ ] Permission-dependent attributes set in `__init__`, never the class body
- [ ] `filter_class` subclassing `HorillaFilterSet`; large FK fields behind `ajax_fields`
- [ ] Form subclassing `base.forms`; `form_valid` returns `self.HttpResponse()`
- [ ] Every label, action and message through `gettext_lazy`
- [ ] `select_related` / `prefetch_related` for every relation a column renders — a list view must
      run the same number of queries at 10 rows and at 500
      (`docs/compliance/bounded-data-access.md`)
- [ ] New model has `HorillaCompanyManager` if the data is per-company
- [ ] Migration generated and committed if a model changed
- [ ] Sidebar entry with `accessibility` and `match_prefixes` as needed
- [ ] `/hr-check` passes
- [ ] Click-tested: create, edit, delete, filter, sort, paginate, export — **and** as a role without
      the permission

## Common failure modes

| Symptom | Cause |
|---|---|
| Create button missing, or visible to everyone | Built in the class body instead of `__init__` |
| Modal does not close after save | `form_valid` returned a redirect instead of `self.HttpResponse()` |
| List does not refresh | `search_swap_target` does not match the container id, or `search_url` points at the wrong route |
| Two sidebar items highlighted | Missing or overlapping `match_prefixes` |
| Filter page slow, or the browser hangs | A large FK rendered as `<option>` tags instead of `ajax_fields` |
| Company's rows leaking | Model left with the default manager (`docs/compliance/company-scoping.md`) |
| Any signed-in employee can read a restricted list | `login_required` without `permission_required`; the generics do not gate the read |
| Columns show raw values or blank | The `columns` tuple names a field that does not exist, or a method not on the model |
