# Translatable UI strings

Horilla ships gettext catalogs (`horilla/locale/`, plus per-app locales) and the portal honours a
user's language. A hard-coded English string is invisible to translators and cannot be fixed without
a code change.

The generic views also read `verbose_name` for column headers and export columns, so an untranslated
field label leaks into more places than the one screen you wrote.

How-to: [`DEVELOPER_GUIDE` — Translations](../DEVELOPER_GUIDE.md#translations).

## Do

- Wrap user-visible strings: `from django.utils.translation import gettext_lazy as _`, then
  `_("Shift Swap Request")`. In templates, `{% translate %}` and `{% blocktranslate %}`.
- Give every model and field a translated `verbose_name` (and `verbose_name_plural` on the model).
- Translate column titles, nav titles, action labels, form labels, validation messages, and the text
  of `messages.success` / `messages.error`.
- Use `blocktranslate` with named placeholders for a sentence that interpolates, so word order can
  change per language.
- Refresh catalogs with the Makefile target:

  ```powershell
  make makemessages
  make compilemessages
  ```

## Do not

- Run a bare `python manage.py makemessages`. The Makefile target passes
  `--ignore=static/build/* --ignore=static/images/ionicons/*`; without them, vendored JavaScript
  identifiers are extracted into every catalog and the diff is enormous and useless.
- Build a sentence by concatenating translated fragments (`_("Leave") + " " + _("approved")`).
- Wrap a value that is not UI text: a URL name, a permission string, a CSS class, a database value,
  a log message.
- Use `gettext` (eager) at module level or in a class body — the language is not known yet. Use
  `gettext_lazy`.
- Commit a `.mo` file edited by hand. Compile them.
