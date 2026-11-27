# Screens go through horilla_views

HR screens in this app are composed from the generic class-based views in
`horilla_views/generic/cbv/views.py` and driven by HTMX. A hand-rolled page misses, for free, what
every other screen has: saved filters, column toggling and ordering, sorting, pagination, bulk
actions, export, the history sidebar, the modal plumbing, and the theme's look.

It also diverges on upgrade. The generics are upstream code; a bespoke page is ours to maintain
forever.

Cookbook and every class attribute: [`reference/SCREENS.md`](../reference/SCREENS.md).
Worked example in the tree: `base/cbv/holidays.py` plus its routes in `base/urls.py`.

## Do

- Build a table as `HorillaListView` with `columns`, `sortby_mapping` and a `filter_class`.
- Build its toolbar as `HorillaNavView` (title, `search_url`, create button, filter panel,
  `actions`), and point `search_swap_target` at the list container.
- Build create and edit as one `HorillaFormView` with `AddOrChangePermissionMixin`, returning
  `self.HttpResponse()` from `form_valid` so the modal closes and the list reloads.
- Build the detail modal as `HorillaDetailedView` with `header` and `body` field lists.
- Give each of those its own URL, and compose them in the template with HTMX attributes
  (`hx-get`, `hx-target="#genericModalBody"`, `data-toggle="oh-modal-toggle"`).
- Use `HorillaCardView` for a card grid, `HorillaTabView` / `HorillaSectionView` for tabbed or
  composed pages, `HorillaProfileView` for employee-profile tabs.
- Put a filter's large FK or M2M field behind `HorillaFilterSet.ajax_fields` rather than rendering
  thousands of `<option>` tags.
- Subclass `base.forms.ModelForm` / `base.forms.Form` so widgets, date and time inputs match.

## Do not

- Write a new full-page template with its own table markup, its own pagination, or its own filter
  form when a generic covers it.
- Add JavaScript that fetches JSON and renders rows client-side. Swap the server-rendered container.
- Build a second export path. Use the list view's, and keep it inside the guards in
  `horilla/export_safety.py`.
- Copy a whole generic view into an app to change one attribute — set the attribute, or override the
  one method.
- Compute permission-dependent class attributes in the class body. There is no request there; do it
  in `__init__`.
- Introduce a front-end framework or build step for an HR screen. The only SPA in this repository is
  the People Operations prototype, which is deliberately separate and not wired to the database
  ([`reference/PEOPLE_OPERATIONS.md`](../reference/PEOPLE_OPERATIONS.md)).
