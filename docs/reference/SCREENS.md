# Screens: the horilla_views cookbook

Every HR screen is composed from the generic class-based views in
`horilla_views/generic/cbv/views.py`. This is how to build one.

**Read the worked example first:** `base/cbv/holidays.py` with its routes in `base/urls.py`
(search for `holiday-`). It is the smallest complete screen in the tree — list, nav, form, detail,
export — and everything below is visible in it.

Rule: [`compliance/screens-use-horilla-views.md`](../compliance/screens-use-horilla-views.md).

## The anatomy

A screen is **several routes**, not one view, assembled in the browser by HTMX:

| Route | Class | Renders |
|---|---|---|
| `…/view/` | a plain `TemplateView` | The page shell that pulls in the rest |
| `…/navbar/` | `HorillaNavView` | Title, search box, create button, filter panel, actions menu |
| `…/filter/` | `HorillaListView` | The table — and also the search/filter endpoint |
| `…/creation/`, `…/update/<pk>/` | `HorillaFormView` | The create / edit modal |
| `…/detail-view/<pk>/` | `HorillaDetailedView` | The detail modal |
| `…/export/` | a `TemplateView` | The export column picker |

The list view's URL doubles as the search endpoint: `search_url` on both the list and the nav view
points at it, and the nav view's `search_swap_target` names the container to swap.

## HorillaListView

```python
@method_decorator(login_required, name="dispatch")
class SwapListView(HorillaListView):
    model = ShiftSwapRequest
    filter_class = SwapFilter

    columns = [
        (_("Employee"), "employee_id"),
        (_("Date"), "requested_on"),
        (_("Status"), "get_status_display"),
    ]
    sortby_mapping = [
        (_("Date"), "requested_on"),
    ]
    header_attrs = {
        "action": """ style="width:180px !important;" """,
    }
    row_attrs = """
        hx-get='{detail_view}?instance_ids={ordered_ids}'
        hx-target="#genericModalBody"
        data-target="#genericModal"
        data-toggle="oh-modal-toggle"
    """
    bulk_update_fields = ["status"]
    quick_export = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = reverse("swap-list")
        self.view_id = "swapList"
        if self.request.user.has_perm("myapp.change_shiftswaprequest"):
            self.action_method = "swap_actions"
```

| Attribute | Does |
|---|---|
| `model`, `filter_class` | The queryset and its filter set |
| `columns` | `(translated label, field or model method)` pairs. A method on the model that returns HTML renders as HTML |
| `sortby_mapping` | Which columns the sort dropdown offers |
| `header_attrs`, `row_attrs` | Raw attribute strings; `row_attrs` supports `{detail_view}` and `{ordered_ids}` placeholders |
| `action_method` | A model method returning the per-row action buttons |
| `bulk_update_fields` | Fields the bulk-update form may set |
| `quick_export` | The one-click export button |
| `search_url` | Where search and filter submit — this view's own URL |
| `view_id` | The DOM id, needed when more than one list is on a page |
| `records_per_page` | Page size; pagination is `horilla.filters.HorillaPaginator` |

Set anything that depends on `self.request` (permissions, the signed-in employee) in `__init__`.
The class body is evaluated once at import time and has no request.

Override `get_queryset()` to scope rows — and scope by the real relationship, not by a URL
parameter the user could change.

## HorillaNavView

```python
@method_decorator(login_required, name="dispatch")
class SwapNavView(HorillaNavView):
    nav_title = _("Shift Swaps")
    template_name = "generic/inline_nav.html"
    filter_body_template = "myapp/swap_filter.html"
    filter_form_context_name = "form"
    filter_instance = SwapFilter()
    search_swap_target = "#listContainer"
    modern_filter = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search_url = reverse("swap-list")
        self.actions = []
        if self.request.user.has_perm("myapp.add_shiftswaprequest"):
            self.create_attrs = f"""
                hx-get="{reverse_lazy('swap-creation')}"
                hx-target="#genericModalBody"
                data-target="#genericModal"
                data-toggle="oh-modal-toggle"
            """
        if has_export_access(self.request, ShiftSwapRequest):
            self.actions.append({"action": _("Export"), "attrs": "…"})
```

- `modern_filter = True` opts into the slide-over filter panel.
- A filter with large FK or M2M fields also declares `ajax_fields` on the **filter class**, not here.
- `actions` entries are `{"action": label, "attrs": raw-attribute-string}`; build them behind
  permission checks.

## HorillaFormView

```python
@method_decorator(login_required, name="dispatch")
class SwapFormView(AddOrChangePermissionMixin, HorillaFormView):
    model = ShiftSwapRequest
    form_class = SwapForm
    new_display_title = _("Create Shift Swap")
    template_name = "myapp/swap_form.html"
    add_perm = "myapp.add_shiftswaprequest"
    change_perm = "myapp.change_shiftswaprequest"

    def form_valid(self, form):
        if form.is_valid():
            message = _("Updated") if form.instance.pk else _("Created")
            form.save()
            messages.success(self.request, message)
            return self.HttpResponse()
        return super().form_valid(form)
```

- One view serves create and edit; the presence of `pk` decides which.
- `return self.HttpResponse()` closes the modal and triggers the list reload. Returning a redirect
  instead breaks the HTMX flow.
- `restrict_company_field = False` when the form's company field may legitimately be blank (meaning
  "all companies") — otherwise the base view forces it to the session company.
- A duplicate route subclasses the form view, overrides `get_queryset()` to return a blank instance
  and `get_required_permission()` to return `add_perm`.

## HorillaDetailedView

```python
@method_decorator(login_required, name="dispatch")
class SwapDetailView(HorillaDetailedView):
    model = ShiftSwapRequest
    title = _("Details")
    template_name = "myapp/swap_detail.html"
    header = {"title": "employee_id", "subtitle": "requested_on", "avatar": "get_avatar"}
    body = [
        (_("Employee"), "employee_id"),
        (_("Date"), "requested_on"),
    ]
    action_method = "detail_view_actions"
```

## The other generics

| Class | Use for |
|---|---|
| `HorillaCardView` | A card grid instead of a table (candidates, assets) |
| `HorillaTabView` + `HorillaTabContentShell` | A tabbed page where each tab loads its own content |
| `HorillaSectionView` | A page composed of several independent sections |
| `HorillaProfileView` + `dispatch_profile_tab` | The employee profile and its tabs |
| `ReloadMessages` | The target that re-renders Django messages after an HTMX action |

## Forms and filters

- Forms subclass `base.forms.ModelForm` / `base.forms.Form` — they apply the theme's widget classes,
  date and time input types and formats, and reload FK querysets per request.
- Filters subclass `horilla.filters.HorillaFilterSet`. A FK or M2M field with hundreds of options
  becomes a server-searched combobox by declaring `ajax_fields`:

  ```python
  class SwapFilter(HorillaFilterSet):
      ajax_fields = {
          "employee_id": {
              "key": "myapp-swap-employee",
              "queryset_fn": lambda request: Employee.objects.all(),
              "display_fn": str,
              "search_fields": ["employee_first_name", "employee_last_name"],
              "placeholder": _("Search employee…"),
              "permission": "employee.view_employee",
          },
      }
  ```

  `queryset_fn` is called per request, so it is where company or subordinate scoping goes. One shared
  endpoint (`horilla_widgets.views.ajax_select_choices`, URL name `horilla-ajax-choices`) serves
  every field registered this way — no new view, no new URL. The full spec is the docstring on
  `HorillaFilterSet` in `horilla/filters.py`.

## The HTMX idioms

| Intent | Attributes |
|---|---|
| Open a modal | `hx-get="<url>" hx-target="#genericModalBody" data-target="#genericModal" data-toggle="oh-modal-toggle"` |
| Refresh the list | Swap the container named by `search_swap_target` |
| Guard a fragment route | `@method_decorator(hx_request_required, name="dispatch")` |
| Re-render messages | Target the `ReloadMessages` view |

Write no JavaScript that fetches JSON and renders rows. Swap server-rendered HTML.

## Checklist for a new screen

- [ ] Routes for shell, nav, list, form, detail — each named, each decorated
- [ ] Permission on every view; the screen hides or disables what the user may not use
- [ ] `filter_class` subclassing `HorillaFilterSet`; large FK fields behind `ajax_fields`
- [ ] Form subclassing `base.forms`; `form_valid` returns `self.HttpResponse()`
- [ ] Every label through `gettext_lazy`
- [ ] `select_related` / `prefetch_related` for every relation a column renders
- [ ] Sidebar entry in `<app>/sidebar.py`, with `accessibility` and `match_prefixes` as needed
- [ ] Click-tested: create, edit, delete, filter, sort, paginate, export, and as a role without the
      permission
