"""
Who sees whose sign in times and daily updates on Company Updates
(HR rule 2026-11-25).

- Super Admin (superuser) and HR Admin (permission
  daily_updates.manage_update_visibility, given through a Horilla permission
  group) see everyone and choose the settings.
- Everyone else sees every colleague whose setting is "Everyone" (the
  default), plus colleagues who chose them under "Selected people", plus
  themselves.
"""

from daily_updates.models import VISIBLE_ADMINS, VISIBLE_SELECTED, UpdateVisibility

PERMISSION = "daily_updates.manage_update_visibility"


def is_admin(user):
    """Super Admin or HR Admin."""
    return bool(user and user.is_authenticated and (user.is_superuser or user.has_perm(PERMISSION)))


def hidden_from(user, viewer, employee_ids):
    """The ids in employee_ids whose sign in and updates user may not see. viewer is user's employee or None."""
    if is_admin(user):
        return set()
    hidden = set()
    viewer_id = getattr(viewer, "pk", None)
    rows = UpdateVisibility.objects.filter(
        employee_id__in=list(employee_ids), mode__in=(VISIBLE_ADMINS, VISIBLE_SELECTED)
    ).prefetch_related("viewers")
    for row in rows:
        if row.employee_id == viewer_id:
            continue
        if row.mode == VISIBLE_SELECTED and viewer_id is not None:
            if any(person.pk == viewer_id for person in row.viewers.all()):
                continue
        hidden.add(row.employee_id)
    return hidden


def can_see(user, viewer, employee_id):
    return employee_id not in hidden_from(user, viewer, [employee_id])
