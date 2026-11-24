from django import template

from workspace_attendance import conf

register = template.Library()


@register.simple_tag
def ws_hide_header_clock():
    """Owner rule (2026-11-12): hide Horilla's green check-in/out timer in the top bar.
    The Workspace card and BevyLoop do sign in and sign out instead."""
    return bool(conf.get("WORKSPACE_HIDE_HEADER_CLOCK"))
