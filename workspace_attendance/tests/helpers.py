"""Shared setup for Workspace attendance tests."""

from datetime import time

from attendance.models import AttendanceGeneralSetting
from base.models import EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule
from horilla.testkit.factories import make_company, make_employee, make_user


def make_day_shift(company, start=time(9, 0), end=time(18, 0), name="Workspace Day"):
    """A shift with a schedule on every weekday, so 'today' always has one."""
    shift = EmployeeShift.objects.create(employee_shift=name)
    shift.company_id.add(company)
    for day in EmployeeShiftDay.objects.all():
        schedule = EmployeeShiftSchedule.objects.create(
            day=day,
            shift_id=shift,
            minimum_working_hour="08:00",
            start_time=start,
            end_time=end,
            is_night_shift=end <= start,
        )
        schedule.company_id.add(company)
    return shift


def make_workspace_employee(username="ws_emp", company=None, shift=None, enable_check_in=True):
    company = company or make_company(f"{username} Co")
    shift = shift or make_day_shift(company)
    AttendanceGeneralSetting.objects.update_or_create(
        company_id=company, defaults={"enable_check_in": enable_check_in}
    )
    user = make_user(username)
    employee = make_employee(
        company=company, email=f"{username}@test.horilla", user=user, shift=shift
    )
    return company, shift, user, employee
