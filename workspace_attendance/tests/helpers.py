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
        company=company,
        email=f"{username}@test.horilla",
        user=user,
        shift=shift,
        first_name=username.replace("_", " ").title().replace(" ", ""),
        last_name="Tester",
    )
    return company, shift, user, employee


def make_forgotten_sign_out(employee, day, user):
    """A past day signed in at 09:00 with no sign out (via Fix My Times, then cleared)."""
    from attendance.models import Attendance, AttendanceActivity
    from workspace_attendance import services

    services.correct_times(employee, day, time(9, 0), time(17, 0), user, "web")
    AttendanceActivity.objects.filter(employee_id=employee, attendance_date=day).update(
        clock_out=None, clock_out_date=None, out_datetime=None
    )
    Attendance.objects.filter(employee_id=employee, attendance_date=day).update(
        attendance_clock_out=None, attendance_clock_out_date=None
    )
