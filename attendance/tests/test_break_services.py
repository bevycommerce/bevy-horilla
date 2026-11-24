"""
Tests for attendance/services/breaks.py and the web views that now call it.

They pin the behaviour of the owner's custom Break and Away feature so the
Smart Workspace refactor (moving the logic out of the views) cannot change it.
"""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import AttendanceActivity, AttendanceBreak, EmployeePresence
from attendance.services.breaks import (
    BreakError,
    clear_away,
    end_break,
    open_activity,
    open_break,
    set_away,
    start_break,
)
from base.models import EmployeeShift, EmployeeShiftDay
from horilla.testkit.factories import make_company, make_employee, make_user

HX = {"HTTP_HX_REQUEST": "true"}


class BreakServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company("Break Co")
        cls.shift = EmployeeShift.objects.create(employee_shift="Day")
        cls.user = make_user("breaker")
        cls.employee = make_employee(
            company=cls.company, email="breaker@test.horilla", user=cls.user, shift=cls.shift
        )

    def _check_in(self, minutes_ago=60):
        start = timezone.localtime() - timedelta(minutes=minutes_ago)
        return AttendanceActivity.objects.create(
            employee_id=self.employee,
            attendance_date=date.today(),
            clock_in_date=date.today(),
            shift_day=EmployeeShiftDay.objects.filter(
                day=date.today().strftime("%A").lower()
            ).first(),
            clock_in=start.time().replace(microsecond=0),
            in_datetime=start,
        )

    def test_invalid_reason_is_rejected(self):
        self._check_in()
        with self.assertRaises(BreakError):
            start_break(self.employee, reason="coffee")
        self.assertIsNone(open_break(self.employee))

    def test_break_needs_check_in(self):
        with self.assertRaises(BreakError):
            start_break(self.employee, reason="prayer")
        self.assertFalse(AttendanceBreak.objects.exists())

    def test_start_closes_activity_and_end_opens_new_one(self):
        activity = self._check_in()
        brk, created = start_break(self.employee, reason="prayer", note="  asr  ")
        self.assertTrue(created)
        self.assertEqual(brk.note, "asr")
        activity.refresh_from_db()
        self.assertIsNotNone(activity.clock_out)
        self.assertIsNone(open_activity(self.employee))

        ended = end_break(self.employee)
        self.assertEqual(ended.pk, brk.pk)
        self.assertIsNotNone(AttendanceBreak.objects.get(pk=brk.pk).end_datetime)
        self.assertIsNotNone(open_activity(self.employee))
        self.assertEqual(
            AttendanceActivity.objects.filter(employee_id=self.employee).count(), 2
        )

    def test_second_start_is_a_no_op(self):
        self._check_in()
        first, _ = start_break(self.employee, reason="prayer")
        second, created = start_break(self.employee, reason="technical_issue")
        self.assertFalse(created)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(AttendanceBreak.objects.count(), 1)

    def test_end_without_break_returns_none(self):
        self._check_in()
        self.assertIsNone(end_break(self.employee))
        self.assertEqual(AttendanceActivity.objects.count(), 1)

    def test_note_is_cut_to_300_characters(self):
        self._check_in()
        brk, _ = start_break(self.employee, reason="prayer", note="x" * 400)
        self.assertEqual(len(brk.note), 300)

    def test_away_needs_check_in_and_can_be_cleared(self):
        with self.assertRaises(BreakError):
            set_away(self.employee)
        self._check_in()
        presence = set_away(self.employee)
        self.assertIsNotNone(presence.away_since)
        clear_away(self.employee)
        self.assertIsNone(EmployeePresence.objects.get(employee_id=self.employee).away_since)

    def test_away_allowed_on_break(self):
        self._check_in()
        start_break(self.employee, reason="prayer")
        self.assertIsNotNone(set_away(self.employee).away_since)


class BreakViewTests(TestCase):
    """The existing web endpoints keep their behaviour after the refactor."""

    @classmethod
    def setUpTestData(cls):
        cls.company = make_company("Break View Co")
        cls.shift = EmployeeShift.objects.create(employee_shift="Day")
        cls.user = make_user("viewbreaker")
        cls.employee = make_employee(
            company=cls.company, email="viewbreaker@test.horilla", user=cls.user, shift=cls.shift
        )

    def setUp(self):
        self.client.force_login(self.user)
        start = timezone.localtime() - timedelta(minutes=30)
        AttendanceActivity.objects.create(
            employee_id=self.employee,
            attendance_date=date.today(),
            clock_in_date=date.today(),
            clock_in=start.time().replace(microsecond=0),
            in_datetime=start,
        )

    def test_break_start_and_end_views(self):
        response = self.client.get(reverse("break-start"), {"reason": "prayer", "note": "n"}, **HX)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(open_break(self.employee))
        response = self.client.get(reverse("break-end"), **HX)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(open_break(self.employee))
        self.assertIsNotNone(open_activity(self.employee))

    def test_break_start_view_rejects_bad_reason(self):
        self.client.get(reverse("break-start"), {"reason": "nap"}, **HX)
        self.assertIsNone(open_break(self.employee))

    def test_set_status_away_and_online(self):
        self.client.get(reverse("set-status"), {"status": "away"}, **HX)
        self.assertIsNotNone(EmployeePresence.objects.get(employee_id=self.employee).away_since)
        start_break(self.employee, reason="prayer")
        self.client.get(reverse("set-status"), {"status": "online"}, **HX)
        self.assertIsNone(EmployeePresence.objects.get(employee_id=self.employee).away_since)
        self.assertIsNone(open_break(self.employee))
        self.assertIsNotNone(open_activity(self.employee))
