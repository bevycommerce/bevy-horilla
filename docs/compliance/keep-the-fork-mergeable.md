# Keep the fork mergeable

This repository is a fork of [horilla/horilla-hr](https://github.com/horilla/horilla-hr). Upstream
keeps shipping: security fixes, Django upgrades, new modules. Every Bevy edit inside an upstream file
is a future merge conflict, and a conflict in `payroll/` or `attendance/` during a security update is
the worst possible time to be re-deciding what our change meant.

The repository already provides the machinery to avoid it: `horilla/inherit/` has a model-field
injection registry with a custom migration autodetector, and a view override registry.

How-to:
[`DEVELOPER_GUIDE` — Extending upstream models](../DEVELOPER_GUIDE.md#extending-upstream-models-without-editing-them).

## Do

- Put Bevy behaviour in a Bevy app: `workspace_attendance`, `daily_updates`, `workspace_reminders`,
  `expense`, or a new one ([new-app playbook](../playbooks/new-app.md)).
- Add a column to an upstream model through `horilla/inherit/` `_inherit` so the field's migration
  lands in the extending app, not in the upstream app's `migrations/`.
- Override an upstream view through `horilla/inherit/view_inherit.py` / `view_registry.py` rather
  than editing the view.
- Put app-level configuration in `<app>/conf.py` with defaults merged from Django settings
  (`workspace_attendance/conf.py` is the pattern), instead of adding keys to
  `horilla/settings/base.py`.
- When an upstream file genuinely must change, keep the edit as small and as obviously-ours as
  possible, and say in the PR what upstream behaviour it alters.
- Record the reason in [`DECISIONS.md`](../DECISIONS.md) when a change deliberately diverges from
  upstream, so the next merge knows whether to keep it.

## Do not

- Scatter Bevy logic through upstream views, models, templates or settings when an extension point
  exists.
- Reformat, re-indent or re-order an upstream file you are editing. A whitespace pass turns a
  three-line change into a whole-file conflict — the exact cost `.gitattributes` records for line
  endings.
- Rename an upstream model, field, URL name or template path.
- Vendor a copy of an upstream module into a Bevy app to change one function.
- Edit `horilla_theme/static/cdn/**`. It is vendored verbatim and excluded from normalisation.
- Delete an upstream feature because Bevy does not use it. Hide it in the sidebar instead.
