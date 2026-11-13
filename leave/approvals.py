"""
leave/approvals.py

Approver based leave approval. The employee picks the approvers while
requesting leave, every picked approver has to approve, and an approver may
add one more approver while approving ("approve and forward").
"""

import contextlib

from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_noop
from django.views.decorators.http import require_http_methods

from employee.models import Employee
from horilla.decorators import login_required
from leave.models import (
    AvailableLeave,
    LeaveApprover,
    LeaverequestComment,
    LeaveRequest,
)
from leave.threading import LeaveMailSendThread
from notifications.signals import notify


def _name(employee):
    get_name = getattr(employee, "get_full_name", None)
    return get_name() if callable(get_name) else str(employee)


def _notify(sender, recipient_employee, verb, redirect):
    with contextlib.suppress(Exception):
        notify.send(
            sender,
            recipient=recipient_employee.employee_user_id,
            verb=verb,
            icon="people-circle",
            redirect=redirect,
        )


HR_LEAD_POSITION = "HR Lead"


def _with_position(position):
    """
    Active employees whose Job Position name is exactly this (ignoring case).
    """
    return [
        e
        for e in Employee.objects.filter(
            is_active=True,
            employee_work_info__job_position_id__job_position__iexact=position,
        )
    ]


def _reporting_manager(employee):
    try:
        return employee.employee_work_info.reporting_manager_id
    except Exception:
        return None


def determine_approvers_with_status(employee):
    """
    Who has to approve this employee's leave, and any problem HR should know.

    Returns (approvers, problems): approvers is a list of (Employee, [reasons]),
    problems a list of messages (empty when everything was found).

    Owner rules (2026-11-13):
    - The reporting manager set in the HR portal always approves.
    - The HR Lead always approves.
    - The PMs of every project the employee is in, read from the project
      approvers Google Sheet (leave/approver_sheet.py).
    - If the sheet cannot be used, or the employee is not in it, only the
      reporting manager and the HR Lead are added, and the HR Lead is told why.
    """
    from leave import approver_sheet

    found = {}
    problems = []

    def add(person, reason):
        if person is None or person.id == employee.id or not person.is_active:
            return
        if person.id in found:
            if reason not in found[person.id][1]:
                found[person.id][1].append(reason)
        else:
            found[person.id] = (person, [reason])

    add(_reporting_manager(employee), "Reporting Manager")
    try:
        pms, sheet_problems = approver_sheet.sheet_approvers(employee)
        for person, reason in pms:
            add(person, reason)
        problems.extend(sheet_problems)
    except approver_sheet.SheetUnavailable as exc:
        problems.append(str(exc))
    for person in _with_position(HR_LEAD_POSITION):
        add(person, HR_LEAD_POSITION)
    return list(found.values()), problems


def determine_approvers(employee):
    """Approvers only, as a list of (Employee, [reasons])."""
    return determine_approvers_with_status(employee)[0]


def _tell_hr_lead(sender, leave_request, problems):
    """Tell every HR Lead that the proper approvers could not all be added, and why."""
    who = _name(leave_request.employee_id)
    reasons = "; ".join(problems)
    verb = (
        f"Proper approvers could not be added for {who}'s leave request: {reasons}. "
        "The reporting manager and HR Lead were added."
    )
    for hr in _with_position(HR_LEAD_POSITION):
        with contextlib.suppress(Exception):
            notify.send(
                sender,
                recipient=hr.employee_user_id,
                verb=verb,
                icon="alert-circle",
                redirect=reverse("leave-my-approvals"),
            )


def create_approver_rows(request, leave_request):
    """
    Called after a leave request is saved. The approvers are worked out by the
    system, saved, and each of them is told.
    """
    if leave_request.status != "requested":
        return
    sender = request.user.employee_get
    approvers, problems = determine_approvers_with_status(leave_request.employee_id)
    if problems:
        _tell_hr_lead(sender, leave_request, problems)
    for employee, _reasons in approvers:
        _, created = LeaveApprover.objects.get_or_create(
            leave_request=leave_request,
            approver=employee,
            defaults={"added_by": sender},
        )
        if created:
            _notify(
                sender,
                employee,
                gettext_noop("You have a leave request to approve."),
                reverse("leave-my-approvals"),
            )


@login_required
def approver_preview(request):
    """
    Approvers the system would pick for the logged in user, for the request form.
    """
    employee = getattr(request.user, "employee_get", None)
    if employee is None:
        return JsonResponse({"approvers": []})
    approvers, problems = determine_approvers_with_status(employee)
    return JsonResponse(
        {
            "approvers": [{"name": _name(person), "reasons": reasons} for person, reasons in approvers],
            "note": "Some approvers could not be found in the project sheet. HR will be told when you send the request." if problems else "",
        }
    )


@login_required
def approver_search(request):
    """
    Employees matching the typed name, for the approvers box.
    """
    query = (request.GET.get("q") or "").strip()
    if len(query) < 1:
        return JsonResponse({"results": []})
    employees = Employee.objects.filter(is_active=True)
    for token in query.split():
        employees = employees.filter(
            Q(employee_first_name__icontains=token)
            | Q(employee_last_name__icontains=token)
            | Q(badge_id__icontains=token)
        )
    me = getattr(request.user, "employee_get", None)
    if me:
        employees = employees.exclude(id=me.id)
    results = [
        {"id": e.id, "name": _name(e), "badge": e.badge_id or ""}
        for e in employees.order_by("employee_first_name")[:10]
    ]
    return JsonResponse({"results": results})


def _pending_rows(employee):
    return (
        LeaveApprover.objects.filter(
            approver=employee, status="pending", leave_request__status="requested"
        )
        .select_related("leave_request", "leave_request__employee_id",
                        "leave_request__leave_type_id")
        .order_by("id")
    )


def _row_dict(row):
    leave_request = row.leave_request
    return {
        "id": row.id,
        "employee": _name(leave_request.employee_id),
        "leave_type": str(leave_request.leave_type_id),
        "start": leave_request.start_date.isoformat(),
        "end": (leave_request.end_date or leave_request.start_date).isoformat(),
        "days": leave_request.requested_days,
        "description": (leave_request.description or "")[:200],
    }


@login_required
def approver_pending(request):
    """
    Waiting approvals of the logged in user, polled by the popup.
    """
    employee = getattr(request.user, "employee_get", None)
    if employee is None:
        return JsonResponse({"items": []})
    return JsonResponse({"items": [_row_dict(r) for r in _pending_rows(employee)[:5]]})


def _balance(leave_request):
    """
    The employee's balance for this leave type, or (None, message).
    """
    try:
        available = AvailableLeave.objects.get(
            leave_type_id=leave_request.leave_type_id,
            employee_id=leave_request.employee_id,
        )
    except AvailableLeave.DoesNotExist:
        return None, "No available leave record found for this employee and leave type."
    days = leave_request.requested_days or 0
    if available.available_days + available.carryforward_days < days:
        return None, "The employee does not have enough leave days to approve this request."
    return available, ""


def _finalize_approve(request, leave_request, available):
    """
    Every approver approved: take the days from the balance and approve.
    """
    days = leave_request.requested_days or 0
    if days > available.carryforward_days:
        taken_from_available = days - available.carryforward_days
        leave_request.approved_carryforward_days = available.carryforward_days
        available.carryforward_days = 0
        available.available_days = available.available_days - taken_from_available
        leave_request.approved_available_days = taken_from_available
    else:
        available.carryforward_days = available.carryforward_days - days
        leave_request.approved_carryforward_days = days
    leave_request.status = "approved"
    leave_request.save()
    available.save()
    _notify(
        request.user.employee_get,
        leave_request.employee_id,
        gettext_noop("Your Leave request has been approved"),
        reverse("user-request-view") + f"?id={leave_request.id}",
    )
    with contextlib.suppress(Exception):
        LeaveMailSendThread(request, leave_request, type="approve").start()


def _finalize_reject(request, leave_request, reason):
    leave_request.status = "rejected"
    leave_request.leave_clashes_count = 0
    leave_request.reject_reason = reason[:255]
    leave_request.save()
    with contextlib.suppress(Exception):
        comment = LeaverequestComment()
        comment.request_id = leave_request
        comment.employee_id = request.user.employee_get
        comment.comment = reason[:255]
        comment.save()
    _notify(
        request.user.employee_get,
        leave_request.employee_id,
        gettext_noop("Your leave request has been rejected."),
        reverse("user-request-view") + f"?id={leave_request.id}",
    )
    with contextlib.suppress(Exception):
        LeaveMailSendThread(request, leave_request, type="reject").start()


def _fail(message, status=400):
    return JsonResponse({"ok": False, "message": message}, status=status)


@login_required
@require_http_methods(["POST"])
def approver_decide(request):
    """
    POST row_id, action=approve|reject, reason (reject), forward_to (approve, optional)
    """
    me = getattr(request.user, "employee_get", None)
    row_id = request.POST.get("row_id", "")
    action = request.POST.get("action")
    if me is None or not row_id.isdigit() or action not in ("approve", "reject"):
        return _fail("Invalid request.")

    with transaction.atomic():
        row = (
            LeaveApprover.objects.select_for_update()
            .filter(id=row_id, approver=me)
            .first()
        )
        if row is None:
            return _fail("You are not an approver of this request.", 403)
        leave_request = LeaveRequest._base_manager.select_for_update().get(
            id=row.leave_request_id
        )
        if row.status != "pending":
            return _fail("You already decided this request.")
        if leave_request.status != "requested":
            return _fail(f"This request is already {leave_request.status}.")

        if action == "reject":
            reason = (request.POST.get("reason") or "").strip()
            if not reason:
                return _fail("Write a reason for rejecting.")
            row.status = "rejected"
            row.comment = reason[:255]
            row.decided_at = timezone.now()
            row.save()
            _finalize_reject(request, leave_request, reason)
            return JsonResponse({"ok": True, "message": "Leave request rejected."})

        # approve, maybe with one more approver added
        forward_id = request.POST.get("forward_to", "")
        forward_to = None
        if forward_id:
            if not forward_id.isdigit():
                return _fail("Invalid person selected.")
            forward_to = Employee.objects.filter(id=forward_id, is_active=True).first()
            if forward_to is None:
                return _fail("The selected person was not found.")
            if forward_to.id in (me.id, leave_request.employee_id_id):
                return _fail("Choose another person to forward to.")
            if LeaveApprover.objects.filter(
                leave_request=leave_request, approver=forward_to
            ).exists():
                return _fail(f"{_name(forward_to)} is already an approver.")

        others_pending = (
            LeaveApprover.objects.filter(leave_request=leave_request, status="pending")
            .exclude(id=row.id)
            .exists()
        )
        will_finish = not others_pending and forward_to is None
        available = None
        if will_finish:
            available, error = _balance(leave_request)
            if available is None:
                return _fail(error)

        row.status = "approved"
        row.decided_at = timezone.now()
        row.save()

        if forward_to is not None:
            LeaveApprover.objects.create(
                leave_request=leave_request, approver=forward_to, added_by=me
            )
            _notify(
                me,
                forward_to,
                gettext_noop("You have a leave request to approve."),
                reverse("leave-my-approvals"),
            )

        if will_finish:
            _finalize_approve(request, leave_request, available)
            return JsonResponse(
                {"ok": True, "message": "Approved. All approvers approved, leave is approved."}
            )
        if forward_to is not None:
            return JsonResponse(
                {"ok": True, "message": f"Approved and sent to {_name(forward_to)}."}
            )
        return JsonResponse(
            {"ok": True, "message": "Approved. Waiting for the other approvers."}
        )


@login_required
def my_approvals(request):
    """
    Page with the requests waiting for the logged in user and the ones decided.
    """
    me = getattr(request.user, "employee_get", None)
    pending, decided = [], []
    if me is not None:
        for row in _pending_rows(me):
            item = _row_dict(row)
            item["others"] = [
                {"name": _name(r.approver), "status": r.get_status_display()}
                for r in row.leave_request.approver_rows.exclude(id=row.id).select_related("approver")
            ]
            pending.append(item)
        done = (
            LeaveApprover.objects.filter(approver=me)
            .exclude(status="pending")
            .select_related("leave_request", "leave_request__employee_id",
                            "leave_request__leave_type_id")
            .order_by("-decided_at")[:30]
        )
        for row in done:
            item = _row_dict(row)
            item["my_status"] = row.get_status_display()
            item["request_status"] = row.leave_request.get_status_display()
            item["decided_at"] = row.decided_at
            decided.append(item)
    return render(
        request,
        "leave/my_approvals.html",
        {"pending": pending, "decided": decided},
    )
