"""
Horilla adapter: the only module of the Smart Workspace that imports Horilla models.

Sign in and sign out reuse Horilla's own functions
(clock_in_attendance_and_activity / clock_out_attendance_and_activity,
late_come / early_out, overtime_calculation), following exactly the steps the
web clock-in/out views take, without needing an HTTP request. Break and Away
reuse attendance.services.breaks (the owner's custom feature).
"""

import ipaddress
from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.utils import timezone
from django.utils.translation import gettext as _

from attendance.methods.utils import (
    activity_datetime,
    format_time,
    geofence_denial_web,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceGeneralSetting,
    AttendanceLateComeEarlyOut,
    EmployeePresence,
)
from attendance.services import breaks as break_service
from attendance.views.clock_in_out import (
    clock_in_attendance_and_activity,
    clock_out_attendance_and_activity,
    early_out,
    late_come,
)
from base.models import AttendanceAllowedIP, EmployeeShiftDay

from .base import AttendanceActionError, BaseAdapter

NOON_SECONDS = strtime_seconds("12:00")


def _shift_day(day_date):
    return EmployeeShiftDay.objects.get(day=day_date.strftime("%A").lower())


def _aware(day_date, clock):
    return timezone.make_aware(datetime.combine(day_date, clock))


def _hhmmss(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime("%H:%M:%S")


class HorillaAdapter(BaseAdapter):
    # ------------------------------------------------------------------ people
    def get_employee(self, user):
        if user is None or not user.is_authenticated:
            return None
        employee = getattr(user, "employee_get", None)
        if employee is None or getattr(employee, "employee_work_info", None) is None:
            return None
        return employee

    def safe_employee_card(self, employee):
        work_info = getattr(employee, "employee_work_info", None)
        department = getattr(work_info, "department_id", None)
        job_position = getattr(work_info, "job_position_id", None)
        try:
            photo = employee.get_avatar()
        except Exception:  # avatar helpers differ between versions; never fail a page for it
            photo = ""
        return {
            "id": employee.pk,
            "name": employee.get_full_name(),
            "photo": photo,
            "department_id": department.pk if department else None,
            "department": str(department) if department else "",
            "job_position": str(job_position) if job_position else "",
        }

    def departments(self):
        from base.models import Department

        return [{"id": d.pk, "name": d.department} for d in Department.objects.order_by("department")]

    def active_employees(self, query=None, department_id=None):
        """Active employees for the company-wide views, optionally filtered by name or department."""
        from django.db.models import Q

        from employee.models import Employee

        employees = Employee.objects.filter(is_active=True).select_related(
            "employee_work_info__department_id", "employee_work_info__job_position_id"
        )
        if query:
            for word in query.split()[:4]:
                employees = employees.filter(
                    Q(employee_first_name__icontains=word) | Q(employee_last_name__icontains=word)
                )
        if department_id:
            employees = employees.filter(employee_work_info__department_id=department_id)
        return list(employees.order_by("employee_first_name", "employee_last_name"))

    def attendance_overview(self, day, employees, now=None):
        """
        One row per employee for the shared dashboard: times, status, late and
        missing-action flags. Only attendance facts, no personal HR data.
        """
        now = now or timezone.localtime()
        ids = [e.pk for e in employees]
        attendances = {
            a.employee_id_id: a
            for a in Attendance.objects.filter(employee_id__in=ids, attendance_date=day)
        }
        working = set(
            AttendanceActivity.objects.filter(
                employee_id__in=ids, attendance_date=day, clock_out__isnull=True
            ).values_list("employee_id", flat=True)
        )
        from attendance.models import AttendanceBreak

        on_break = set(
            AttendanceBreak.objects.filter(
                employee_id__in=ids, attendance_date=day, end_datetime__isnull=True
            ).values_list("employee_id", flat=True)
        )
        late = set(
            AttendanceLateComeEarlyOut.objects.filter(
                attendance_id__in=[a.pk for a in attendances.values()], type="late_come"
            ).values_list("employee_id", flat=True)
        )
        rows = []
        for employee in employees:
            att = attendances.get(employee.pk)
            if employee.pk in on_break:
                status = "on_break"
            elif employee.pk in working:
                status = "working"
            elif att is not None and att.attendance_clock_out is not None:
                status = "signed_out"
            else:
                status = "not_signed_in"
            missing = []
            window = self.shift_window(employee, day)
            if att is None and window is not None and now >= window[0]:
                missing.append("sign_in")
            if att is not None and att.attendance_clock_out is None:
                if status not in ("working", "on_break") or day < now.date():
                    missing.append("sign_out")
            rows.append(
                {
                    "employee": self.safe_employee_card(employee),
                    "status": status,
                    "sign_in": att.attendance_clock_in.strftime("%H:%M") if att and att.attendance_clock_in else None,
                    "sign_out": att.attendance_clock_out.strftime("%H:%M") if att and att.attendance_clock_out else None,
                    "worked": att.attendance_worked_hour if att else None,
                    "late": employee.pk in late,
                    "missing": missing,
                    "has_shift_today": window is not None,
                }
            )
        return rows

    # ----------------------------------------------------------------- state
    def get_state(self, employee, now=None):
        now = now or timezone.localtime()
        running_break = break_service.open_break(employee)
        running_activity = break_service.open_activity(employee)

        if running_activity is not None:
            work_date = running_activity.attendance_date
        elif running_break is not None:
            work_date = running_break.attendance_date
        else:
            work_date = now.date()
        attendance = (
            Attendance.objects.filter(employee_id=employee, attendance_date=work_date)
            .order_by("-id")
            .first()
        )
        if attendance is None and running_activity is None and running_break is None:
            # night shift: yesterday's attendance may still be the current one
            attendance = (
                Attendance.objects.filter(
                    employee_id=employee,
                    attendance_date=work_date - timedelta(days=1),
                    attendance_clock_out__isnull=True,
                )
                .order_by("-id")
                .first()
            )
            if attendance is not None:
                work_date = attendance.attendance_date

        worked_seconds = 0
        signed_in_at = None
        for activity in AttendanceActivity.objects.filter(
            employee_id=employee, attendance_date=work_date
        ).order_by("clock_in_date", "clock_in", "id"):
            start = activity.in_datetime or _aware(activity.clock_in_date, activity.clock_in)
            if signed_in_at is None:
                signed_in_at = timezone.localtime(start)
            if activity.clock_out is None:
                worked_seconds += max(0, int((now - start).total_seconds()))
            else:
                in_dt, out_dt = activity_datetime(activity)
                worked_seconds += max(0, int((out_dt - in_dt).total_seconds()))

        away_since = None
        presence = EmployeePresence.objects.filter(employee_id=employee).first()
        if presence and presence.away_since and (running_activity or running_break):
            latest_resume = running_activity.in_datetime if running_activity else None
            if latest_resume is None or presence.away_since >= latest_resume:
                away_since = presence.away_since

        if running_break is not None:
            status = "on_break"
        elif running_activity is not None:
            status = "away" if away_since else "working"
        elif attendance is not None and attendance.attendance_clock_out is not None:
            status = "signed_out"
        else:
            status = "not_signed_in"

        signed_out_at = None
        if status == "signed_out":
            signed_out_at = timezone.localtime(
                _aware(attendance.attendance_clock_out_date, attendance.attendance_clock_out)
            )

        return {
            "status": status,
            "work_date": work_date,
            "attendance_id": attendance.pk if attendance else None,
            "signed_in_at": signed_in_at,
            "signed_out_at": signed_out_at,
            "worked_seconds": worked_seconds,
            "timer_running": status in ("working", "away"),
            "break": (
                {
                    "reason": running_break.reason,
                    "reason_label": str(running_break.get_reason_display()),
                    "note": running_break.note,
                    "started_at": timezone.localtime(running_break.start_datetime),
                    "seconds": running_break.duration_seconds(),
                }
                if running_break
                else None
            ),
            "away_since": timezone.localtime(away_since) if away_since else None,
        }

    def attendance_by_day(self, employee, start, end):
        """{date: {"sign_in": time, "sign_out": time, "worked": "HH:MM"}} for a date range."""
        return {
            a.attendance_date: {
                "sign_in": a.attendance_clock_in,
                "sign_out": a.attendance_clock_out,
                "worked": a.attendance_worked_hour,
            }
            for a in Attendance.objects.filter(
                employee_id=employee, attendance_date__gte=start, attendance_date__lte=end
            )
        }

    def break_reasons(self):
        from attendance.models import AttendanceBreak

        return [{"value": k, "label": str(v)} for k, v in AttendanceBreak.REASON_CHOICES]

    # ------------------------------------------------------------ rules
    def check_allowed(self, employee, client_ip=None, coords=None):
        company = employee.get_company()
        settings_row = (
            AttendanceGeneralSetting.objects.filter(company_id=company).first()
            or AttendanceGeneralSetting.objects.filter(company_id=None).first()
        )
        if settings_row is None or not settings_row.enable_check_in:
            raise AttendanceActionError(
                _("The attendance check-in/check-out feature has not been enabled for your company."),
                code="disabled",
            )

        allowed = AttendanceAllowedIP.objects.filter(company_id=company).first()
        if allowed and allowed.is_enabled:
            ip_ok = False
            for network in (allowed.additional_data or {}).get("allowed_ips", []):
                try:
                    if client_ip and ipaddress.ip_address(client_ip) in ipaddress.ip_network(
                        network, strict=False
                    ):
                        ip_ok = True
                        break
                except ValueError:
                    continue
            if not ip_ok:
                raise AttendanceActionError(
                    _("Restricted: your current network is not authorized for attendance."),
                    code="ip_restricted",
                )

        coords = coords or {}
        fake_request = SimpleNamespace(
            GET={
                "latitude": coords.get("latitude"),
                "longitude": coords.get("longitude"),
            },
            user=SimpleNamespace(employee_get=employee),
        )
        geo_error = geofence_denial_web(fake_request, company)
        if geo_error:
            raise AttendanceActionError(str(geo_error), code="location_restricted")

    # ----------------------------------------------------------- actions
    def sign_in(self, employee, now):
        """Same steps as attendance.views.clock_in_out.clock_in, without a request."""
        shift = employee.employee_work_info.shift_id
        date_today = now.date()
        attendance_date = date_today
        day = _shift_day(date_today)
        now_hm = now.strftime("%H:%M")
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        if start_sec > end_sec and NOON_SECONDS > strtime_seconds(now_hm):
            # night shift that started yesterday (Horilla's noon-to-noon rule)
            attendance_date = date_today - timedelta(days=1)
            day = _shift_day(attendance_date)
            minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        return clock_in_attendance_and_activity(
            employee=employee,
            date_today=date_today,
            attendance_date=attendance_date,
            day=day,
            now=now_hm,
            shift=shift,
            minimum_hour=minimum_hour,
            start_time=start_sec,
            end_time=end_sec,
            in_datetime=now,
        )

    def sign_out(self, employee, now):
        """Same steps as attendance.views.clock_in_out.clock_out, without a request."""
        shift = employee.employee_work_info.shift_id
        date_today = now.date()
        day = _shift_day(date_today)
        latest = Attendance.objects.filter(employee_id=employee).order_by("id", "attendance_date").last()
        if latest is not None:
            if not latest.attendance_day:
                latest.attendance_day = _shift_day(latest.attendance_date)
                latest.save(update_fields=["attendance_day"])
            day = latest.attendance_day
        now_hm = now.strftime("%H:%M")
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        attendance = clock_out_attendance_and_activity(
            employee=employee, date_today=date_today, now=now_hm, out_datetime=now
        )
        if attendance:
            if not attendance.late_come_early_out.filter(type="early_out").exists():
                if attendance.is_night_shift():
                    next_date = attendance.attendance_date + timedelta(days=1)
                    if attendance.attendance_date == date_today or (
                        NOON_SECONDS >= strtime_seconds(now_hm) and date_today == next_date
                    ):
                        early_out(attendance=attendance, start_time=start_sec, end_time=end_sec, shift=shift)
                elif attendance.attendance_date == date_today:
                    early_out(attendance=attendance, start_time=start_sec, end_time=end_sec, shift=shift)
        return attendance

    def start_break(self, employee, reason, note, now):
        try:
            return break_service.start_break(employee, reason=reason, note=note, now=now)
        except break_service.BreakError as error:
            raise AttendanceActionError(str(error.args[0]), code="break_invalid") from error

    def end_break(self, employee, now):
        return break_service.end_break(employee, now=now)

    def set_away(self, employee, now):
        try:
            return break_service.set_away(employee, now=now)
        except break_service.BreakError as error:
            raise AttendanceActionError(str(error.args[0]), code="not_signed_in") from error

    def clear_away(self, employee):
        return break_service.clear_away(employee)

    def mark_valid_for_payroll(self, attendance):
        if not attendance.attendance_validated:
            attendance.attendance_validated = True
            attendance.save()
        return attendance

    # -------------------------------------------------------- corrections
    def correct_times(self, employee, work_date, sign_in, sign_out, now):
        """
        Fix My Times on Horilla records. sign_in / sign_out are datetime.time or None.
        Returns (attendance, changes) with changes = [(field, old, new), ...].
        """
        attendance = Attendance.objects.filter(employee_id=employee, attendance_date=work_date).first()
        if attendance is not None and attendance.is_validate_request:
            raise AttendanceActionError(
                _("This day has a pending attendance request. Cancel that request first, then fix the times here."),
                code="pending_request",
            )
        if break_service.open_break(employee) and break_service.open_break(employee).attendance_date == work_date:
            raise AttendanceActionError(
                _("You are on a break for this day. End the break first."), code="on_break"
            )

        shift = employee.employee_work_info.shift_id
        day = _shift_day(work_date)
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        night_shift = start_sec > end_sec

        activities = list(
            AttendanceActivity.objects.filter(employee_id=employee, attendance_date=work_date).order_by(
                "clock_in_date", "clock_in", "id"
            )
        )
        changes = []

        def out_date_for(in_date, in_clock, out_clock):
            if out_clock > in_clock:
                return in_date
            if night_shift:
                return in_date + timedelta(days=1)
            raise AttendanceActionError(_("Sign out must be after sign in."), code="order")

        def not_future(day_date, clock, label):
            if _aware(day_date, clock) > now:
                raise AttendanceActionError(
                    _("%(what)s cannot be in the future.") % {"what": label}, code="future"
                )

        # ---------------- no record for that day yet
        if attendance is None:
            if sign_in is None:
                raise AttendanceActionError(
                    _("There is no attendance for this day. Enter a sign in time."), code="missing_sign_in"
                )
            not_future(work_date, sign_in, _("Sign in"))
            attendance = Attendance(
                employee_id=employee,
                shift_id=shift,
                work_type_id=employee.employee_work_info.work_type_id,
                attendance_date=work_date,
                attendance_day=day,
                attendance_clock_in=sign_in,
                attendance_clock_in_date=work_date,
                minimum_hour=minimum_hour,
            )
            attendance.save()
            activity = AttendanceActivity(
                employee_id=employee,
                attendance_date=work_date,
                clock_in_date=work_date,
                shift_day=day,
                clock_in=sign_in,
                in_datetime=_aware(work_date, sign_in),
            )
            changes.append(("created", "", work_date.isoformat()))
            changes.append(("sign_in", "", _hhmmss(sign_in)))
            if sign_out is not None:
                out_date = out_date_for(work_date, sign_in, sign_out)
                not_future(out_date, sign_out, _("Sign out"))
                activity.clock_out = sign_out
                activity.clock_out_date = out_date
                activity.out_datetime = _aware(out_date, sign_out)
                changes.append(("sign_out", "", _hhmmss(sign_out)))
            activity.save()
            activities = [activity]
        else:
            if not activities:
                # an attendance row without activities (e.g. imported): rebuild one from the row
                if attendance.attendance_clock_in is None and sign_in is None:
                    raise AttendanceActionError(_("Enter a sign in time."), code="missing_sign_in")
                base_in = sign_in or attendance.attendance_clock_in
                activity = AttendanceActivity(
                    employee_id=employee,
                    attendance_date=work_date,
                    clock_in_date=attendance.attendance_clock_in_date or work_date,
                    shift_day=day,
                    clock_in=base_in,
                    in_datetime=_aware(attendance.attendance_clock_in_date or work_date, base_in),
                )
                if attendance.attendance_clock_out is not None:
                    activity.clock_out = attendance.attendance_clock_out
                    activity.clock_out_date = attendance.attendance_clock_out_date or work_date
                    activity.out_datetime = _aware(activity.clock_out_date, activity.clock_out)
                activity.save()
                activities = [activity]

            first, last = activities[0], activities[-1]
            if sign_in is not None:
                not_future(work_date, sign_in, _("Sign in"))
                limit_clock = first.clock_out
                if limit_clock is not None:
                    first_out = _aware(first.clock_out_date, first.clock_out)
                    if _aware(work_date, sign_in) >= first_out:
                        raise AttendanceActionError(
                            _("Sign in must be before your first break or sign out."), code="order"
                        )
                old = _hhmmss(attendance.attendance_clock_in)
                first.clock_in = sign_in
                first.clock_in_date = work_date
                first.in_datetime = _aware(work_date, sign_in)
                first.save()
                if old != _hhmmss(sign_in):
                    changes.append(("sign_in", old, _hhmmss(sign_in)))
            if sign_out is not None:
                last_in_clock = last.clock_in if last is not first or sign_in is None else sign_in
                out_date = out_date_for(last.clock_in_date, last_in_clock, sign_out)
                not_future(out_date, sign_out, _("Sign out"))
                old = _hhmmss(attendance.attendance_clock_out)
                last.clock_out = sign_out
                last.clock_out_date = out_date
                last.out_datetime = _aware(out_date, sign_out)
                last.save()
                if old != _hhmmss(sign_out):
                    changes.append(("sign_out", old, _hhmmss(sign_out)))

        # ---------------- recompute the day the way Horilla does on sign out
        activities = list(
            AttendanceActivity.objects.filter(employee_id=employee, attendance_date=work_date).order_by(
                "clock_in_date", "clock_in", "id"
            )
        )
        first, last = activities[0], activities[-1]
        attendance.attendance_clock_in = first.clock_in
        attendance.attendance_clock_in_date = first.clock_in_date
        if last.clock_out is not None:
            attendance.attendance_clock_out = last.clock_out
            attendance.attendance_clock_out_date = last.clock_out_date
        else:
            attendance.attendance_clock_out = None
            attendance.attendance_clock_out_date = None
        total = 0
        for activity in activities:
            if activity.clock_out is not None:
                in_dt, out_dt = activity_datetime(activity)
                total += max(0, int((out_dt - in_dt).total_seconds()))
        attendance.attendance_worked_hour = format_time(total)
        if not attendance.attendance_day:
            attendance.attendance_day = day
        attendance.attendance_overtime = overtime_calculation(attendance)
        attendance.save()

        # late / early flags: recompute, but never remove one that already has a penalty
        flags = AttendanceLateComeEarlyOut.objects.filter(attendance_id=attendance)
        for flag in flags:
            if not flag.penaltyaccounts_set.exists():
                flag.delete()
        attendance = Attendance.objects.get(pk=attendance.pk)
        if attendance.attendance_clock_in and not flags.filter(type="late_come").exists():
            late_come(attendance=attendance, start_time=start_sec, end_time=end_sec, shift=shift)
        if attendance.attendance_clock_out and not flags.filter(type="early_out").exists():
            early_out(attendance=attendance, start_time=start_sec, end_time=end_sec, shift=shift)

        return attendance, changes

    # ---------------------------------------------------------- schedule
    def shift_window(self, employee, day_date):
        shift = getattr(employee.employee_work_info, "shift_id", None)
        if shift is None:
            return None
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=_shift_day(day_date), shift=shift)
        if start_sec == 0 and end_sec == 0:
            return None
        start = _aware(day_date, time(start_sec // 3600, (start_sec % 3600) // 60))
        end_day = day_date + timedelta(days=1) if end_sec <= start_sec else day_date
        end = _aware(end_day, time(end_sec // 3600, (end_sec % 3600) // 60))
        return start, end
