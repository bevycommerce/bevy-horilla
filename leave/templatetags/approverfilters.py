"""
leave/templatetags/approverfilters.py
"""

from django import template

register = template.Library()


@register.filter(name="approver_rows")
def approver_rows(leave_request):
    """
    Approvers of a leave request with the text to show for each.
    A pending approver of a request that is already decided shows no status.
    """
    try:
        rows = list(leave_request.approver_rows.select_related("approver"))
    except Exception:
        return []
    decided = leave_request.status in ("approved", "rejected", "cancelled")
    result = []
    for row in rows:
        if row.status == "pending" and decided:
            label, color = "-", "#888"
        elif row.status == "pending":
            label, color = "Pending", "#e9910d"
        elif row.status == "approved":
            label, color = "Approved", "#1a8f3c"
        else:
            label, color = "Rejected", "#d93025"
        get_name = getattr(row.approver, "get_full_name", None)
        result.append(
            {
                "name": get_name() if callable(get_name) else str(row.approver),
                "label": label,
                "color": color,
                "comment": row.comment,
            }
        )
    return result
