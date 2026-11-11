"""
daily_updates/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Daily Updates")
IMG_SRC = "images/ui/daily_updates.svg"

SUBMENUS = [
    {
        "menu": _("My Updates"),
        "redirect": reverse_lazy("daily-updates"),
    },
    {
        "menu": _("Company Updates"),
        "redirect": reverse_lazy("daily-updates-company"),
    },
]
