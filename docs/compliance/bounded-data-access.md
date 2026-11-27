# Bounded data access

A screen's query count scales with the batch, never with how many employees, attendance rows,
candidates or payslips exist. The portal runs on a small server (2 GB of RAM on the staging box,
per [`v1-to-v2.md`](../v1-to-v2.md)), one gunicorn process set behind nginx, so a per-row query in a
list view is not a style problem — it is the page timing out for HR at month end.

Existing loops in upstream code are legacy. This rule binds **new and modified** data access; do not
copy a per-row loop from a sibling screen.

How-to: [`DEVELOPER_GUIDE` — Queries that stay bounded](../DEVELOPER_GUIDE.md#queries-that-stay-bounded).

## Do

- Read once per relation: `filter(id__in=[...])`, `select_related` for FKs you render,
  `prefetch_related` for M2M and reverse sets, then index the result into a dict by id.
- Hoist loop-invariant reads (company settings, shift, leave type, payroll structure) out of the loop.
- Aggregate and count in SQL: `aggregate`, `annotate`, `Count`, `Sum`, `groupby`. A total shown to a
  user comes from the database, never from summing a paginated list.
- Keep pagination. `HorillaListView` paginates through `horilla.filters.HorillaPaginator`; a custom
  context that passes a full queryset to a template bypasses it.
- Clamp any page size, limit or offset that comes from the request to a named default and maximum.
- Put an index on a FK you filter, order or count on, and commit the migration for it.
- Read an export in chunks rather than building the whole result set in memory — and send its cells
  through `horilla/export_safety.py`, which is a separate concern (spreadsheet formula injection,
  see [`DEVELOPER_GUIDE`](../DEVELOPER_GUIDE.md#queries-that-stay-bounded)) and equally required.
- Verify before the PR: run the changed path against a few hundred rows locally with query logging
  on, and confirm the query count does not grow with the row count.

## Do not

- Put an ORM call inside a `for` loop over employees, attendance rows, leave requests or candidates
  — directly, or through a helper that takes a single id.
- Render a related field (`employee_id.employee_work_info.department_id`) in a list column without
  `select_related` on that path.
- Use a relation `_count` annotation on a list read over a table that grows per employee without
  checking the plan.
- Load an employee's full history, every audit revision, or every attendance activity on a page that
  shows a summary.
- Return an unpaginated list from an API endpoint. DRF's `PAGE_SIZE` default is 20 for a reason;
  overriding it per view needs a stated maximum.
- Add a dashboard tile whose query walks every row for every company on every page load.
