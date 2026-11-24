"""
expense/views.py
"""

import os
from datetime import date, timedelta

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from expense.models import Expense, ExpenseProof
from horilla.decorators import login_required

MAX_FILES = 10
MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt", ".rtf",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp",
    ".xls", ".xlsx", ".csv", ".ods",
}


def _get_employee(request):
    try:
        return request.user.employee_get
    except Exception:
        return None


@login_required
def expense_submit(request):
    """
    Expense submission form
    """
    employee = _get_employee(request)
    values = {}
    errors = {}

    if request.method == "POST":
        values = {
            "expense_date": (request.POST.get("expense_date") or "").strip(),
            "vendor": (request.POST.get("vendor") or "").strip(),
            "description": (request.POST.get("description") or "").strip(),
            "amount": (request.POST.get("amount") or "").strip(),
        }
        files = request.FILES.getlist("proofs")

        if employee is None:
            errors["general"] = _("Your employee profile is missing.")

        parsed_date = None
        try:
            parsed_date = date.fromisoformat(values["expense_date"])
        except ValueError:
            errors["expense_date"] = _("Enter a valid date.")

        if not values["vendor"]:
            errors["vendor"] = _("This field is required.")
        elif len(values["vendor"]) > 150:
            errors["vendor"] = _("Maximum 150 characters.")

        if not values["description"]:
            errors["description"] = _("This field is required.")
        elif len(values["description"]) > 500:
            errors["description"] = _("Maximum 500 characters.")

        amount = None
        if not values["amount"].isdigit() or int(values["amount"]) <= 0:
            errors["amount"] = _("Enter a whole number greater than zero, no decimals.")
        else:
            amount = int(values["amount"])

        if not files:
            errors["proofs"] = _("Upload at least one proof of purchase.")
        elif len(files) > MAX_FILES:
            errors["proofs"] = _("You can upload up to 10 files.")
        else:
            for item in files:
                ext = os.path.splitext(item.name)[1].lower()
                if ext not in ALLOWED_EXTENSIONS:
                    errors["proofs"] = _(
                        "%(name)s is not a supported file type. Use PDF, document, image or spreadsheet."
                    ) % {"name": item.name}
                    break
                if item.size > MAX_FILE_BYTES:
                    errors["proofs"] = _("%(name)s is larger than 10 MB.") % {
                        "name": item.name
                    }
                    break

        if not errors:
            expense = Expense.objects.create(
                employee_id=employee,
                expense_date=parsed_date,
                vendor=values["vendor"],
                description=values["description"],
                amount=amount,
            )
            for item in files:
                ExpenseProof.objects.create(
                    expense=expense, file=item, original_name=item.name[:255]
                )
            messages.success(request, _("Expense submitted."))
            return redirect("expense-log")

    return render(
        request,
        "expense/expense_form.html",
        {"values": values, "errors": errors, "today": date.today().isoformat()},
    )


@login_required
def expense_log(request):
    """
    Expense log. Users with the view expense permission see every employee,
    everyone else sees only their own expenses.
    """
    today = date.today()

    def read_date(name, default):
        try:
            return date.fromisoformat(request.GET.get(name, ""))
        except ValueError:
            return default

    date_from = read_date("from", today.replace(day=1))
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    date_to = read_date("to", next_month - timedelta(days=1))

    expenses = (
        Expense.objects.filter(expense_date__range=(date_from, date_to))
        .select_related("employee_id")
        .prefetch_related("proofs")
    )
    can_view_all = request.user.is_superuser or request.user.has_perm(
        "expense.view_expense"
    )
    if not can_view_all:
        employee = _get_employee(request)
        expenses = expenses.filter(employee_id=employee) if employee else expenses.none()

    total = expenses.aggregate(total=Sum("amount"))["total"] or 0
    rows = []
    for item in expenses.order_by("-expense_date", "-id"):
        get_name = getattr(item.employee_id, "get_full_name", None)
        rows.append(
            {
                "employee": get_name() if callable(get_name) else str(item.employee_id),
                "expense_date": item.expense_date,
                "vendor": item.vendor,
                "description": item.description,
                "amount": item.amount,
                "proofs": list(item.proofs.all()),
                "created_at": item.created_at,
            }
        )

    return render(
        request,
        "expense/expense_log.html",
        {
            "rows": rows,
            "total": total,
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "can_view_all": can_view_all,
        },
    )
