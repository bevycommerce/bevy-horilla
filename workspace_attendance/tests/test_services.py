"""
Phase 1 tests: Workspace sign in/out, breaks, idempotency, company rules,
Fix My Times, audit history and payroll compatibility.
"""

import threading
from datetime import datetime, time, timedelta
from unittest import mock

from django.db import connection
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from attendance.models import (
    Attendance,
    AttendanceActivity,
    AttendanceBreak,
    AttendanceLateComeEarlyOut,
)
from workspace_attendance import services
from workspace_attendance.models import (
    AttendanceCorrectionLog,
    WorkspaceAttendanceEvent,
    WorkspaceAttendanceMeta,
    WorkspaceIdempotencyKey,
)
from workspace_attendance.services import WorkspaceError

from .helpers import make_workspace_employee


class SignInOutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("signer")

    def test_sign_in_creates_horilla_records_and_event(self):
        status, body = services.sign_in(self.employee, "web")
        self.assertEqual(status, 200)
        self.assertTrue(body["changed"])
        self.assertEqual(body["state"]["status"], "working")
        attendance = Attendance.objects.get(employee_id=self.employee)
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)
        event = WorkspaceAttendanceEvent.objects.get(employee=self.employee, action="sign_in")
        self.assertEqual(event.source, "web")
        self.assertEqual(event.attendance_id, attendance.pk)
        self.assertIsNotNone(event.recorded_at)
        self.assertTrue(WorkspaceAttendanceMeta.objects.filter(attendance=attendance).exists())

    def test_sign_in_again_reports_the_new_session_start(self):
        _, body = services.sign_in(self.employee, "web")
        self.assertEqual(body["state"]["session_started_at"], body["state"]["signed_in_at"])
        _, body = services.sign_out(self.employee, "web")
        self.assertIsNone(body["state"]["session_started_at"])
        first = AttendanceActivity.objects.get(employee_id=self.employee)
        early = timezone.make_aware(datetime.combine(first.clock_in_date, time(0, 1)))
        AttendanceActivity.objects.filter(pk=first.pk).update(
            clock_in=time(0, 1), clock_out=time(0, 2), in_datetime=early, out_datetime=early + timedelta(minutes=1)
        )
        _, body = services.sign_in(self.employee, "desktop")
        state = body["state"]
        self.assertEqual(state["status"], "working")
        self.assertIn("T00:01", state["signed_in_at"])
        self.assertNotIn("T00:01", state["session_started_at"])
        self.assertGreater(state["session_started_at"], state["signed_in_at"])

    def test_duplicate_sign_in_does_nothing(self):
        services.sign_in(self.employee, "web")
        status, body = services.sign_in(self.employee, "desktop")
        self.assertEqual(status, 200)
        self.assertFalse(body["changed"])
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)
        self.assertEqual(WorkspaceAttendanceEvent.objects.filter(action="sign_in").count(), 1)

    def test_sign_out_validates_for_payroll(self):
        services.sign_in(self.employee, "web")
        status, body = services.sign_out(self.employee, "desktop")
        self.assertTrue(body["changed"])
        self.assertEqual(body["state"]["status"], "signed_out")
        attendance = Attendance.objects.get(employee_id=self.employee)
        self.assertTrue(attendance.attendance_validated)
        self.assertIsNotNone(attendance.attendance_clock_out)

    @override_settings(WORKSPACE_AUTO_VALIDATE=False)
    def test_auto_validate_switch_leaves_horilla_rule_alone(self):
        services.sign_in(self.employee, "web")
        services.sign_out(self.employee, "web")
        meta = WorkspaceAttendanceMeta.objects.get()
        self.assertEqual(meta.last_source, "web")

    def test_duplicate_sign_out_does_nothing(self):
        services.sign_in(self.employee, "web")
        services.sign_out(self.employee, "web")
        status, body = services.sign_out(self.employee, "web")
        self.assertFalse(body["changed"])
        self.assertEqual(WorkspaceAttendanceEvent.objects.filter(action="sign_out").count(), 1)

    def test_sign_out_without_sign_in(self):
        status, body = services.sign_out(self.employee, "web")
        self.assertEqual(status, 200)
        self.assertFalse(body["changed"])
        self.assertFalse(Attendance.objects.exists())

    def test_sign_out_while_on_break_ends_break_first(self):
        services.sign_in(self.employee, "web")
        services.start_break(self.employee, "prayer", "", "web")
        self.assertEqual(services.get_state(self.employee)["status"], "on_break")
        status, body = services.sign_out(self.employee, "web")
        self.assertTrue(body["changed"])
        self.assertFalse(AttendanceBreak.objects.filter(end_datetime__isnull=True).exists())
        self.assertFalse(AttendanceActivity.objects.filter(clock_out__isnull=True).exists())

    def test_away_status_and_back(self):
        services.sign_in(self.employee, "web")
        services.set_away(self.employee, True, "web")
        self.assertEqual(services.get_state(self.employee)["status"], "away")
        services.set_away(self.employee, False, "web")
        self.assertEqual(services.get_state(self.employee)["status"], "working")

    def test_away_needs_sign_in(self):
        with self.assertRaises(WorkspaceError):
            services.set_away(self.employee, True, "web")

    def test_unknown_source_rejected(self):
        with self.assertRaises(WorkspaceError):
            services.sign_in(self.employee, "telepathy")


class IdempotencyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("idem")

    def test_same_key_replays_answer(self):
        s1, b1 = services.sign_in(self.employee, "desktop", key="key-0001-abcdef")
        services.sign_out(self.employee, "desktop", key="key-0002-abcdef")
        s2, b2 = services.sign_in(self.employee, "desktop", key="key-0001-abcdef")
        self.assertTrue(b2["replayed"])
        self.assertEqual(b1["message"], b2["message"])
        # the replay did not sign in again after the sign out
        self.assertEqual(services.get_state(self.employee)["status"], "signed_out")
        self.assertEqual(WorkspaceAttendanceEvent.objects.filter(action="sign_in").count(), 1)

    def test_key_reused_for_other_action_conflicts(self):
        services.sign_in(self.employee, "desktop", key="key-0003-abcdef")
        with self.assertRaises(WorkspaceError) as ctx:
            services.sign_out(self.employee, "desktop", key="key-0003-abcdef")
        self.assertEqual(ctx.exception.status, 409)

    def test_bad_key_rejected(self):
        with self.assertRaises(WorkspaceError):
            services.sign_in(self.employee, "desktop", key="no spaces allowed!")

    def test_failed_action_does_not_store_key(self):
        with mock.patch(
            "workspace_attendance.adapters.horilla.HorillaAdapter.check_allowed",
            side_effect=services.AttendanceActionError("blocked", code="ip_restricted"),
        ):
            with self.assertRaises(WorkspaceError):
                services.sign_in(self.employee, "desktop", key="key-0004-abcdef")
        self.assertFalse(WorkspaceIdempotencyKey.objects.exists())
        status, body = services.sign_in(self.employee, "desktop", key="key-0004-abcdef")
        self.assertTrue(body["changed"])

    def test_cleanup_removes_old_keys(self):
        services.sign_in(self.employee, "desktop", key="key-0005-abcdef")
        WorkspaceIdempotencyKey.objects.update(created_at=timezone.now() - timedelta(days=30))
        self.assertEqual(services.cleanup_idempotency_keys(), 1)


class SimultaneousRequestTests(TransactionTestCase):
    """Two clicks at the same moment must produce one sign in."""

    def setUp(self):
        self.company, self.shift, self.user, self.employee = make_workspace_employee("racer")

    def test_parallel_sign_in(self):
        errors = []
        barrier = threading.Barrier(2)

        def click():
            try:
                barrier.wait()
                services.sign_in(self.employee, "desktop")
            except Exception as error:  # pragma: no cover - reported below
                errors.append(error)
            finally:
                connection.close()

        threads = [threading.Thread(target=click) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)
        self.assertEqual(WorkspaceAttendanceEvent.objects.filter(action="sign_in").count(), 1)

    def test_parallel_same_idempotency_key(self):
        results = []
        barrier = threading.Barrier(2)

        def click():
            try:
                barrier.wait()
                results.append(services.sign_in(self.employee, "desktop", key="race-key-000001"))
            finally:
                connection.close()

        threads = [threading.Thread(target=click) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(results), 2)
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)


class CompanyRuleTests(TestCase):
    def test_disabled_check_in_is_refused(self):
        _, _, _, employee = make_workspace_employee("disabled", enable_check_in=False)
        with self.assertRaises(WorkspaceError) as ctx:
            services.sign_in(employee, "desktop")
        self.assertEqual(ctx.exception.status, 403)
        self.assertFalse(Attendance.objects.exists())

    def test_ip_restriction_applies(self):
        from base.models import AttendanceAllowedIP

        company, _, _, employee = make_workspace_employee("iprule")
        AttendanceAllowedIP.objects.create(
            company_id=company, is_enabled=True, additional_data={"allowed_ips": ["10.0.0.0/8"]}
        )
        with self.assertRaises(WorkspaceError) as ctx:
            services.sign_in(employee, "desktop", client_ip="203.0.113.5")
        self.assertEqual(ctx.exception.code, "ip_restricted")
        status, body = services.sign_in(employee, "desktop", client_ip="10.1.2.3")
        self.assertTrue(body["changed"])


class FixMyTimesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("fixer")

    def day(self, n):
        return timezone.localdate() - timedelta(days=n)

    def test_create_missing_day(self):
        day = self.day(2)
        status, body = services.correct_times(self.employee, day, time(9, 0), time(17, 30), self.user, "web")
        self.assertTrue(body["changed"])
        att = Attendance.objects.get(employee_id=self.employee, attendance_date=day)
        self.assertEqual(att.attendance_worked_hour, "08:30")
        self.assertTrue(att.attendance_validated)
        self.assertEqual(att.attendance_overtime, "00:30")
        fields = set(AttendanceCorrectionLog.objects.values_list("field", flat=True))
        self.assertEqual(fields, {"created", "sign_in", "sign_out"})

    def test_forgot_sign_out_yesterday(self):
        day = self.day(1)
        services.correct_times(self.employee, day, time(9, 0), None, self.user, "web")
        att = Attendance.objects.get(attendance_date=day)
        self.assertIsNone(att.attendance_clock_out)
        services.correct_times(self.employee, day, None, time(18, 0), self.user, "desktop")
        att.refresh_from_db()
        self.assertEqual(att.attendance_clock_out, time(18, 0))
        self.assertEqual(att.attendance_worked_hour, "09:00")
        self.assertTrue(att.attendance_validated)
        log = AttendanceCorrectionLog.objects.filter(field="sign_out").latest("id")
        self.assertEqual(log.old_value, "")
        self.assertEqual(log.new_value, "18:00:00")
        self.assertEqual(log.source, "desktop")

    def test_change_existing_times_keeps_breaks(self):
        day = self.day(3)
        services.correct_times(self.employee, day, time(9, 0), time(18, 0), self.user, "web")
        # add a break in the middle the way the break feature records it
        first = AttendanceActivity.objects.get(attendance_date=day)
        first.clock_out = time(13, 0)
        first.out_datetime = timezone.make_aware(timezone.datetime.combine(day, time(13, 0)))
        first.save()
        AttendanceActivity.objects.create(
            employee_id=self.employee,
            attendance_date=day,
            clock_in_date=day,
            clock_in=time(14, 0),
            in_datetime=timezone.make_aware(timezone.datetime.combine(day, time(14, 0))),
            clock_out=time(18, 0),
            clock_out_date=day,
        )
        services.correct_times(self.employee, day, time(8, 30), time(18, 30), self.user, "web")
        att = Attendance.objects.get(attendance_date=day)
        # 08:30-13:00 (4:30) + 14:00-18:30 (4:30) = 9:00, the 1h break is still excluded
        self.assertEqual(att.attendance_worked_hour, "09:00")
        self.assertEqual(AttendanceActivity.objects.filter(attendance_date=day).count(), 2)

    def test_window_limit(self):
        with self.assertRaises(WorkspaceError) as ctx:
            services.correct_times(self.employee, self.day(31), time(9, 0), time(17, 0), self.user, "web")
        self.assertEqual(ctx.exception.code, "outside_window")
        # the boundary day itself is allowed
        services.correct_times(self.employee, self.day(30), time(9, 0), time(17, 0), self.user, "web")

    @override_settings(WORKSPACE_CORRECTION_WINDOW_DAYS=7)
    def test_window_is_configurable(self):
        with self.assertRaises(WorkspaceError):
            services.correct_times(self.employee, self.day(8), time(9, 0), time(17, 0), self.user, "web")

    def test_future_rejected(self):
        with self.assertRaises(WorkspaceError):
            services.correct_times(
                self.employee, timezone.localdate() + timedelta(days=1), time(9, 0), None, self.user, "web"
            )
        later = (timezone.localtime() + timedelta(hours=2)).time().replace(second=0, microsecond=0)
        if later > timezone.localtime().time():  # skip near midnight
            with self.assertRaises(WorkspaceError) as ctx:
                services.correct_times(self.employee, timezone.localdate(), later, None, self.user, "web")
            self.assertEqual(ctx.exception.code, "future")

    def test_sign_out_before_sign_in_rejected(self):
        with self.assertRaises(WorkspaceError) as ctx:
            services.correct_times(self.employee, self.day(2), time(17, 0), time(9, 0), self.user, "web")
        self.assertEqual(ctx.exception.code, "order")
        self.assertFalse(Attendance.objects.filter(attendance_date=self.day(2)).exists())

    def test_nothing_given(self):
        with self.assertRaises(WorkspaceError):
            services.correct_times(self.employee, self.day(2), None, None, self.user, "web")

    def test_pending_hr_request_blocks(self):
        day = self.day(4)
        services.correct_times(self.employee, day, time(9, 0), time(17, 0), self.user, "web")
        Attendance.objects.filter(attendance_date=day).update(is_validate_request=True)
        with self.assertRaises(WorkspaceError) as ctx:
            services.correct_times(self.employee, day, time(8, 0), None, self.user, "web")
        self.assertEqual(ctx.exception.code, "pending_request")

    def test_log_is_immutable(self):
        services.correct_times(self.employee, self.day(2), time(9, 0), time(17, 0), self.user, "web")
        log = AttendanceCorrectionLog.objects.first()
        log.new_value = "tampered"
        with self.assertRaises(ValueError):
            log.save()
        with self.assertRaises(ValueError):
            log.delete()

    def test_late_flag_recomputed_when_corrected(self):
        with mock.patch(
            "attendance.views.clock_in_out.enable_late_come_early_out_tracking",
            return_value={"tracking": True},
        ):
            day = self.day(2)
            services.correct_times(self.employee, day, time(10, 0), time(18, 0), self.user, "web")
            att = Attendance.objects.get(attendance_date=day)
            self.assertTrue(AttendanceLateComeEarlyOut.objects.filter(attendance_id=att, type="late_come").exists())
            services.correct_times(self.employee, day, time(8, 55), None, self.user, "web")
            self.assertFalse(AttendanceLateComeEarlyOut.objects.filter(attendance_id=att, type="late_come").exists())


class PayrollCompatibilityTests(TestCase):
    """A Workspace day must count in payroll exactly like an HR-validated day."""

    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("payee")

    def test_corrected_day_is_counted_by_payroll(self):
        from payroll.methods.methods import get_attendance

        day = timezone.localdate() - timedelta(days=2)
        services.correct_times(self.employee, day, time(9, 0), time(17, 0), self.user, "web")
        data = get_attendance(self.employee, day, day)
        self.assertIn(day, data["present_on"])

    def test_unvalidated_horilla_day_still_excluded(self):
        """Workspace does not change the rule for rows it never touched."""
        from horilla.testkit.factories import make_attendance
        from payroll.methods.methods import get_attendance

        day = timezone.localdate() - timedelta(days=5)
        make_attendance(employee=self.employee, attendance_date=day, validated=False)
        self.assertNotIn(day, get_attendance(self.employee, day, day)["present_on"])

    def test_overtime_still_needs_hr_approval(self):
        day = timezone.localdate() - timedelta(days=2)
        services.correct_times(self.employee, day, time(8, 0), time(19, 0), self.user, "web")
        att = Attendance.objects.get(attendance_date=day)
        self.assertEqual(att.attendance_overtime, "03:00")
        self.assertFalse(att.attendance_overtime_approve)
