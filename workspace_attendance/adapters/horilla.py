"""
Horilla adapter: the only module of the Smart Workspace that imports Horilla models.

Sign in and sign out reuse Horilla's own functions
(clock_in_attendance_and_activity / clock_out_attendance_and_activity,
late_come / early_out, overtime_calculation), following exactly the steps the
web clock-in/out views take, without needing an HTTP request. Break and Away
reuse attendance.services.breaks.
"""

import ipaddress
from datetime import datetime, time, timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import gettext as _

from attendance.methods.utils import (
    activity_datetime,
    format_time,
    overtime_calculation,
    shift_schedule_today,
    strtime_seconds,
)
from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceBreak,
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


def _activity_start(activity):
    """When an activity started, or None for a row without a check-in date."""
    if activity.in_datetime:
        return activity.in_datetime
    if activity.clock_in_date and activity.clock_in:
        return _aware(activity.clock_in_date, activity.clock_in)
    return None


def _work_info(employee):
    """The employee's work information, or None when the row is missing."""
    try:
        return employee.employee_work_info
    except ObjectDoesNotExist:
        return None


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
        except (
            Exception
        ):  # avatar helpers differ between versions; never fail a page for it
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

        return [
            {"id": d.pk, "name": d.department}
            for d in Department.objects.order_by("department")
        ]

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
                    Q(employee_first_name__icontains=word)
                    | Q(employee_last_name__icontains=word)
                )
        if department_id:
            employees = employees.filter(
                employee_work_info__department_id=department_id
            )
        return list(employees.order_by("employee_first_name", "employee_last_name"))

    def is_visible_employee(self, employee_id):
        """
        Whether employee_id is one of the people the company-wide views show the
        current viewer (same company scope as active_employees).
        """
        from employee.models import Employee

        return Employee.objects.filter(is_active=True, pk=employee_id).exists()

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
        windows = {}  # one schedule lookup per shift for this day
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
            shift_id = getattr(_work_info(employee), "shift_id_id", None)
            if shift_id not in windows:
                windows[shift_id] = self.shift_window(employee, day)
            window = windows[shift_id]
            if att is None and window is not None and now >= window[0]:
                missing.append("sign_in")
            if att is not None and att.attendance_clock_out is None:
                if status not in ("working", "on_break") or day < now.date():
                    missing.append("sign_out")
            rows.append(
                {
                    "employee": self.safe_employee_card(employee),
                    "status": status,
                    "sign_in": (
                        att.attendance_clock_in.strftime("%H:%M")
                        if att and att.attendance_clock_in
                        else None
                    ),
                    "sign_out": (
                        att.attendance_clock_out.strftime("%H:%M")
                        if att and att.attendance_clock_out
                        else None
                    ),
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
        session_started_at = None
        # Ending a break opens a new activity at the break's end time. That is not a
        # new sign in, so the session start stays the time before the break.
        break_ends = [
            b.end_datetime
            for b in AttendanceBreak.objects.filter(
                employee_id=employee,
                attendance_date__in=(work_date, work_date - timedelta(days=1)),
                end_datetime__isnull=False,
            ).only("end_datetime")
        ]
        session_start = None
        for activity in AttendanceActivity.objects.filter(
            employee_id=employee, attendance_date=work_date
        ).order_by("clock_in_date", "clock_in", "id"):
            start = _activity_start(activity)
            if start is None:
                # incomplete legacy row (no check-in date): no time is invented
                continue
            if signed_in_at is None:
                signed_in_at = timezone.localtime(start)
            resumed_after_break = any(
                abs((start - end).total_seconds()) <= 1 for end in break_ends
            )
            if session_start is None or not resumed_after_break:
                session_start = start
            if running_activity is not None and activity.pk == running_activity.pk:
                session_started_at = timezone.localtime(session_start)
            if activity.clock_out is None:
                worked_seconds += max(0, int((now - start).total_seconds()))
            else:
                # stored timestamps keep seconds, so the timer does not jump when
                # a break closes the activity; older rows fall back to clock times
                if activity.in_datetime and activity.out_datetime:
                    in_dt, out_dt = activity.in_datetime, activity.out_datetime
                elif activity.clock_in_date and activity.clock_out_date:
                    in_dt, out_dt = activity_datetime(activity)
                else:
                    continue
                worked_seconds += max(0, int((out_dt - in_dt).total_seconds()))

        if running_activity is not None and session_started_at is None:
            running_start = _activity_start(running_activity)
            if running_start is not None:
                session_started_at = timezone.localtime(running_start)

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
            if attendance.attendance_clock_out_date is not None:
                signed_out_at = timezone.localtime(
                    _aware(
                        attendance.attendance_clock_out_date,
                        attendance.attendance_clock_out,
                    )
                )
            else:
                # no checkout date on the row: use the last closed activity's
                # stored end time if there is one, never a guessed date
                last = (
                    AttendanceActivity.objects.filter(
                        employee_id=employee,
                        attendance_date=work_date,
                        out_datetime__isnull=False,
                    )
                    .order_by("-out_datetime")
                    .first()
                )
                if last is not None:
                    signed_out_at = timezone.localtime(last.out_datetime)

        return {
            "status": status,
            "work_date": work_date,
            "attendance_id": attendance.pk if attendance else None,
            "signed_in_at": signed_in_at,
            # start of the current sign-in (differs from signed_in_at after "Sign In Again")
            "session_started_at": session_started_at,
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
                employee_id=employee,
                attendance_date__gte=start,
                attendance_date__lte=end,
            )
        }

    def break_reasons(self):
        from attendance.models import AttendanceBreak

        return [
            {"value": k, "label": str(v)} for k, v in AttendanceBreak.REASON_CHOICES
        ]

    # ------------------------------------------------------------ rules
    @staticmethod
    def _check_in_setting(employee):
        """
        The AttendanceGeneralSetting row that decides whether check-in is enabled.

        With a company chosen in the portal's company switcher (web), this is the
        same lookup as the header Check-In button (attendance.views.clock_in_out):
        "all" uses the global row, a company uses only that company's row.
        Without a chosen company (the desktop API has no session), the
        employee's own company row is used, then the global row.
        """
        from base.models import Company
        from horilla.horilla_middlewares import _thread_locals

        request = getattr(_thread_locals, "request", None)
        session = getattr(request, "session", None)
        selected = session.get("selected_company") if session is not None else None
        if selected == "all":
            return AttendanceGeneralSetting.objects.filter(company_id=None).first()
        if selected:
            company = Company.objects.filter(id=selected).first()
            return AttendanceGeneralSetting.objects.filter(company_id=company).first()
        return (
            AttendanceGeneralSetting.objects.filter(
                company_id=employee.get_company()
            ).first()
            or AttendanceGeneralSetting.objects.filter(company_id=None).first()
        )

    def check_allowed(self, employee, client_ip=None, coords=None):
        # coords is accepted from the card and the desktop app but not checked:
        # the header Check-In button on this portal has no location rule either.
        settings_row = self._check_in_setting(employee)
        if settings_row is None or not settings_row.enable_check_in:
            raise AttendanceActionError(
                _(
                    "The attendance check-in/check-out feature has not been enabled for your company."
                ),
                code="disabled",
            )

        # Same office network rule as the header Check-In button
        # (attendance.views.clock_in_out.clock_in).
        allowed = AttendanceAllowedIP.objects.first()
        if allowed and allowed.is_enabled:
            ip_ok = False
            for network in (allowed.additional_data or {}).get("allowed_ips", []):
                try:
                    if client_ip and ipaddress.ip_address(
                        client_ip
                    ) in ipaddress.ip_network(network, strict=False):
                        ip_ok = True
                        break
                except ValueError:
                    continue
            if not ip_ok:
                raise AttendanceActionError(
                    _("You cannot mark attendance from this network"),
                    code="ip_restricted",
                )

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
            minimum_hour, start_sec, end_sec = shift_schedule_today(
                day=day, shift=shift
            )
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
        # the row clock_out_attendance_and_activity finalizes: the one of the
        # activity being closed, else the latest row
        open_activity = (
            AttendanceActivity.objects.filter(
                employee_id=employee, clock_out__isnull=True
            )
            .order_by("attendance_date", "id")
            .last()
        )
        latest = None
        if open_activity is not None:
            latest = (
                Attendance.objects.filter(
                    employee_id=employee, attendance_date=open_activity.attendance_date
                )
                .order_by("-id")
                .first()
            )
        if latest is None:
            latest = (
                Attendance.objects.filter(employee_id=employee)
                .order_by("-attendance_date", "-id")
                .first()
            )
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
                        NOON_SECONDS >= strtime_seconds(now_hm)
                        and date_today == next_date
                    ):
                        early_out(
                            attendance=attendance,
                            start_time=start_sec,
                            end_time=end_sec,
                            shift=shift,
                        )
                elif attendance.attendance_date == date_today:
                    early_out(
                        attendance=attendance,
                        start_time=start_sec,
                        end_time=end_sec,
                        shift=shift,
                    )
        return attendance

    def start_break(self, employee, reason, note, now):
        try:
            return break_service.start_break(
                employee, reason=reason, note=note, now=now
            )
        except break_service.BreakError as error:
            raise AttendanceActionError(
                str(error.args[0]), code="break_invalid"
            ) from error

    def end_break(self, employee, now):
        return break_service.end_break(employee, now=now)

    def set_away(self, employee, now):
        try:
            return break_service.set_away(employee, now=now)
        except break_service.BreakError as error:
            raise AttendanceActionError(
                str(error.args[0]), code="not_signed_in"
            ) from error

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
        attendance = Attendance.objects.filter(
            employee_id=employee, attendance_date=work_date
        ).first()
        if attendance is not None and attendance.is_validate_request:
            raise AttendanceActionError(
                _(
                    "This day has a pending attendance request. Cancel that request first, then fix the times here."
                ),
                code="pending_request",
            )
        if (
            break_service.open_break(employee)
            and break_service.open_break(employee).attendance_date == work_date
        ):
            raise AttendanceActionError(
                _("You are on a break for this day. End the break first."),
                code="on_break",
            )

        shift = employee.employee_work_info.shift_id
        day = _shift_day(work_date)
        minimum_hour, start_sec, end_sec = shift_schedule_today(day=day, shift=shift)
        night_shift = start_sec > end_sec

        activities = list(
            AttendanceActivity.objects.filter(
                employee_id=employee, attendance_date=work_date
            ).order_by("clock_in_date", "clock_in", "id")
        )
        changes = []

        def out_date_for(in_date, in_clock, out_clock):
            if out_clock > in_clock:
                out_date = in_date
            # equal times are never read as a 24-hour overnight interval
            elif night_shift and out_clock < in_clock:
                out_date = in_date + timedelta(days=1)
            else:
                raise AttendanceActionError(
                    _("Sign out must be after sign in."), code="order"
                )
            # a shift ends at the latest on the morning after its work date
            if out_date > work_date + timedelta(days=1):
                raise AttendanceActionError(
                    _("Sign out must be within this shift."), code="order"
                )
            return out_date

        def in_date_for(clock):
            """
            The calendar date of a sign-in typed as a time only: on a night shift,
            a time before the shift's end (e.g. 01:15 on a 22:00-06:00 shift)
            belongs to the morning after the work date.
            """
            if night_shift and strtime_seconds(clock.strftime("%H:%M")) < end_sec:
                return work_date + timedelta(days=1)
            return work_date

        def not_future(day_date, clock, label):
            if _aware(day_date, clock) > now:
                raise AttendanceActionError(
                    _("%(what)s cannot be in the future.") % {"what": label},
                    code="future",
                )

        # ---------------- no record for that day yet
        if attendance is None:
            if sign_in is None:
                raise AttendanceActionError(
                    _("There is no attendance for this day. Enter a sign in time."),
                    code="missing_sign_in",
                )
            in_date = in_date_for(sign_in)
            not_future(in_date, sign_in, _("Sign in"))
            window = self.shift_window(employee, work_date)
            shift_over = (
                window[1] <= now if window is not None else work_date < now.date()
            )
            if sign_out is None and shift_over:
                # a sign-in alone would leave this past day signed in until now
                raise AttendanceActionError(
                    _("This day is over. Enter the sign out time too."),
                    code="missing_sign_out",
                )
            attendance = Attendance(
                employee_id=employee,
                shift_id=shift,
                work_type_id=employee.employee_work_info.work_type_id,
                attendance_date=work_date,
                attendance_day=day,
                attendance_clock_in=sign_in,
                attendance_clock_in_date=in_date,
                minimum_hour=minimum_hour,
            )
            attendance.save()
            activity = AttendanceActivity(
                employee_id=employee,
                attendance_date=work_date,
                clock_in_date=in_date,
                shift_day=day,
                clock_in=sign_in,
                in_datetime=_aware(in_date, sign_in),
            )
            changes.append(("created", "", work_date.isoformat()))
            changes.append(("sign_in", "", _hhmmss(sign_in)))
            if sign_out is not None:
                out_date = out_date_for(in_date, sign_in, sign_out)
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
                    raise AttendanceActionError(
                        _("Enter a sign in time."), code="missing_sign_in"
                    )
                base_in = sign_in or attendance.attendance_clock_in
                activity = AttendanceActivity(
                    employee_id=employee,
                    attendance_date=work_date,
                    clock_in_date=attendance.attendance_clock_in_date or work_date,
                    shift_day=day,
                    clock_in=base_in,
                    in_datetime=_aware(
                        attendance.attendance_clock_in_date or work_date, base_in
                    ),
                )
                if attendance.attendance_clock_out is not None:
                    activity.clock_out = attendance.attendance_clock_out
                    activity.clock_out_date = (
                        attendance.attendance_clock_out_date or work_date
                    )
                    activity.out_datetime = _aware(
                        activity.clock_out_date, activity.clock_out
                    )
                activity.save()
                activities = [activity]

            first, last = activities[0], activities[-1]
            if sign_in is not None:
                in_date = in_date_for(sign_in)
                not_future(in_date, sign_in, _("Sign in"))
                # When both times of a single activity change, the new pair is
                # checked together below (sign out must be after the new sign in).
                both_on_one = sign_out is not None and first is last
                if first.clock_out is not None and not both_on_one:
                    first_out = _aware(first.clock_out_date, first.clock_out)
                    if _aware(in_date, sign_in) >= first_out:
                        raise AttendanceActionError(
                            _("Sign in must be before your first break or sign out."),
                            code="order",
                        )
                old = _hhmmss(attendance.attendance_clock_in)
                first.clock_in = sign_in
                first.clock_in_date = in_date
                first.in_datetime = _aware(in_date, sign_in)
                first.save()
                if old != _hhmmss(sign_in):
                    changes.append(("sign_in", old, _hhmmss(sign_in)))
            if sign_out is not None:
                last_in_clock = (
                    last.clock_in if last is not first or sign_in is None else sign_in
                )
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
            AttendanceActivity.objects.filter(
                employee_id=employee, attendance_date=work_date
            ).order_by("clock_in_date", "clock_in", "id")
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
        old_overtime = attendance.attendance_overtime
        attendance.attendance_overtime = overtime_calculation(attendance)
        if (
            attendance.pk
            and attendance.attendance_overtime_approve
            and attendance.attendance_overtime != old_overtime
        ):
            # HR approved this day's overtime; a self-correction must not change
            # the approved amount that payroll pays (the whole fix is rolled back)
            raise AttendanceActionError(
                _(
                    "HR has already approved overtime for this day. Ask HR to change these times."
                ),
                code="overtime_approved",
            )
        attendance.save()

        # late / early flags: recompute, but never remove one that already has a penalty
        flags = AttendanceLateComeEarlyOut.objects.filter(attendance_id=attendance)
        for flag in flags:
            if not flag.penaltyaccounts_set.exists():
                flag.delete()
        attendance = Attendance.objects.get(pk=attendance.pk)
        if (
            attendance.attendance_clock_in
            and not flags.filter(type="late_come").exists()
        ):
            late_come(
                attendance=attendance,
                start_time=start_sec,
                end_time=end_sec,
                shift=shift,
            )
        if (
            attendance.attendance_clock_out
            and not flags.filter(type="early_out").exists()
        ):
            early_out(
                attendance=attendance,
                start_time=start_sec,
                end_time=end_sec,
                shift=shift,
            )

        return attendance, changes

    # ---------------------------------------------------------- schedule
    def shift_window(self, employee, day_date):
        shift = getattr(_work_info(employee), "shift_id", None)
        if shift is None:
            return None
        minimum_hour, start_sec, end_sec = shift_schedule_today(
            day=_shift_day(day_date), shift=shift
        )
        if start_sec == 0 and end_sec == 0:
            return None
        start = _aware(day_date, time(start_sec // 3600, (start_sec % 3600) // 60))
        end_day = day_date + timedelta(days=1) if end_sec <= start_sec else day_date
        end = _aware(end_day, time(end_sec // 3600, (end_sec % 3600) // 60))
        return start, end
