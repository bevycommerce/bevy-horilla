"""Shared setup for Workspace attendance tests."""

from datetime import time

from django.contrib.auth.models import User

from attendance.models import Attendance, AttendanceGeneralSetting
from base.models import Company, EmployeeShift, EmployeeShiftDay, EmployeeShiftSchedule
from employee.models import Employee, EmployeeWorkInformation
from horilla.horilla_middlewares import _thread_locals

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def forget_last_request():
    """
    HorillaModel.save() stamps created_by from the last request seen on this
    thread. A request left over from an earlier test points at a user that no
    longer exists, so test data is created with no request in place.
    """
    _thread_locals.request = None


def make_shift_days():
    """The seven EmployeeShiftDay rows (seeded by load_data on a real portal)."""
    for name in WEEKDAYS:
        if not EmployeeShiftDay.objects.filter(day=name).exists():
            EmployeeShiftDay(day=name).save()


def make_department(name):
    """A Department (1.0 models pass save() arguments to clean(), so no objects.create())."""
    from base.models import Department

    department = Department(department=name)
    department.save()
    return department


def make_company(name="Test Corp"):
    return Company.objects.create(
        company=name,
        hq=True,
        address="1 Test St",
        country="US",
        state="CA",
        city="LA",
        zip="90001",
    )


def make_user(username, password="pass", is_superuser=False):
    email = f"{username}@test.horilla"
    if is_superuser:
        return User.objects.create_superuser(
            username=username, email=email, password=password
        )
    return User.objects.create_user(username=username, email=email, password=password)


def make_employee(
    *, company, email, first_name="Test", last_name="Employee", user=None, shift=None
):
    """An Employee with work information in ``company`` (and ``shift`` when given)."""
    employee = Employee(
        employee_first_name=first_name,
        employee_last_name=last_name,
        email=email,
        phone="9999999999",
    )
    if user is not None:
        employee.employee_user_id = user
    employee.save()
    updates = {"company_id": company}
    if shift is not None:
        updates["shift_id"] = shift
    if not EmployeeWorkInformation.objects.filter(employee_id=employee).update(
        **updates
    ):
        EmployeeWorkInformation.objects.create(employee_id=employee, **updates)
    return Employee.objects.select_related("employee_work_info").get(pk=employee.pk)


def make_attendance(
    *,
    employee,
    attendance_date,
    validated=True,
    clock_in="09:00:00",
    clock_out="18:00:00",
):
    """One finished 8-hour day (Attendance.save() derives the rest)."""
    return Attendance.objects.create(
        employee_id=employee,
        attendance_date=attendance_date,
        attendance_clock_in_date=attendance_date,
        attendance_clock_in=clock_in,
        attendance_clock_out_date=attendance_date,
        attendance_clock_out=clock_out,
        attendance_worked_hour="08:00",
        minimum_hour="08:00",
        attendance_validated=validated,
    )


def make_day_shift(company, start=time(9, 0), end=time(18, 0), name="Workspace Day"):
    """A shift with a schedule on every weekday, so 'today' always has one."""
    make_shift_days()
    # 1.0 models pass save() arguments to clean(), so objects.create() fails here
    shift = EmployeeShift(employee_shift=name)
    shift.save()
    shift.company_id.add(company)
    for day in EmployeeShiftDay.objects.all():
        schedule = EmployeeShiftSchedule(
            day=day,
            shift_id=shift,
            minimum_working_hour="08:00",
            start_time=start,
            end_time=end,
            is_night_shift=end <= start,
        )
        schedule.save()
        schedule.company_id.add(company)
    return shift


def make_workspace_employee(
    username="ws_emp", company=None, shift=None, enable_check_in=True
):
    forget_last_request()
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
