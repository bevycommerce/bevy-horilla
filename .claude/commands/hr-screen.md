---
description: Add or change an HR screen (list, nav, form, detail) built on horilla_views
argument-hint: "[what the screen should show or do]"
---

Build or change the screen described: $ARGUMENTS

Load the `horilla-screen` skill and follow it. It covers the generic class-based views, which routes
a screen needs, where permission-dependent attributes must go, and the HTMX idioms.

Before writing code:

1. Find the owning app in [`docs/reference/APP_MAP.md`](../../docs/reference/APP_MAP.md). A new
   screen almost always belongs in an existing app.
2. Read `base/cbv/holidays.py` and its routes in `base/urls.py` (search `holiday-`). It is the
   smallest complete screen in the tree and the pattern to copy.
3. Decide the access rule first: who may see this, who may change it, which existing permission
   covers it.
4. Say in chat which routes you will add, which permission gates each, and whether the data is
   company-scoped. Wait for approval.

Then implement per [`docs/reference/SCREENS.md`](../../docs/reference/SCREENS.md) and finish its
checklist. Close with `/hr-check` and a click-test — including as a role that should **not** see the
screen.
