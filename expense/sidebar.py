"""
expense/sidebar.py
"""

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

MENU = _("Expenses")
IMG_SRC = "images/ui/expense.svg"

SUBMENUS = [
    {
        "menu": _("Submit Expense"),
        "redirect": reverse_lazy("expense-submit"),
    },
    {
        "menu": _("Expense Log"),
        "redirect": reverse_lazy("expense-log"),
    },
]
