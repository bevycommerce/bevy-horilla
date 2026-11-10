"""
expense/models.py
"""

import os
from uuid import uuid4

from django.db import models
from django.utils.translation import gettext_lazy as _

from employee.models import Employee


def proof_upload_path(instance, filename):
    """
    Keep the original extension, replace the name so uploads never clash.
    """
    ext = os.path.splitext(filename)[1].lower()
    return f"expense/proofs/{uuid4().hex}{ext}"


class Expense(models.Model):
    """
    One submitted expense
    """

    employee_id = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        related_name="employee_expenses",
        verbose_name=_("Employee"),
    )
    expense_date = models.DateField(verbose_name=_("Expense Date"))
    vendor = models.CharField(max_length=150, verbose_name=_("Vendor / Company"))
    description = models.CharField(
        max_length=500, verbose_name=_("Description of Expense")
    )
    amount = models.PositiveIntegerField(
        verbose_name=_("Expense Amount (Local Currency)")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = _("Expense")
        verbose_name_plural = _("Expenses")

    def __str__(self):
        return f"{self.employee_id} {self.expense_date} {self.vendor} {self.amount}"


class ExpenseProof(models.Model):
    """
    A proof of purchase file of an expense
    """

    expense = models.ForeignKey(
        Expense, on_delete=models.CASCADE, related_name="proofs"
    )
    file = models.FileField(upload_to=proof_upload_path)
    original_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.original_name
