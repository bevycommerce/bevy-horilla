"""Web card and Fix My Times views."""

from datetime import time, timedelta

from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import Attendance, AttendanceActivity, AttendanceBreak
from horilla.testkit.factories import make_user
from workspace_attendance import services, views
from workspace_attendance.models import AttendanceCorrectionLog

from .helpers import make_workspace_employee

HX = {"HTTP_HX_REQUEST": "true"}


class CardTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("card_emp")

    def setUp(self):
        self.client.force_login(self.user)

    def post(self, name, data=None):
        return self.client.post(reverse(name), data or {}, **HX)


class CardRenderTests(CardTestBase):
    def test_card_renders_for_employee(self):
        response = self.client.get(reverse("workspace-card"), **HX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Start Your Day")
        self.assertContains(response, "Not Signed In")
        self.assertContains(response, "Fix My Times")

    def test_card_empty_for_user_without_employee(self):
        # Called directly: Horilla's middleware logs such users out before a view is reached.
        request = RequestFactory().get(reverse("workspace-card"), **HX)
        request.user = make_user("no_employee")
        response = views.workspace_card(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_unauthenticated_redirects_to_login(self):
        self.client.logout()
        for name in ("workspace-card", "workspace-fix-times"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("login", response["Location"])
        response = self.client.post(reverse("workspace-sign-in"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Attendance.objects.exists())

    def test_actions_refuse_get(self):
        for name in ("workspace-sign-in", "workspace-sign-out", "workspace-break-start",
                     "workspace-break-end", "workspace-away", "workspace-fix-times-save"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 405, name)

    def test_template_renders_every_status(self):
        base = {"break_reasons": [{"value": "prayer", "label": "Prayer"}], "window_days": 30}
        states = {
            "not_signed_in": ("Start Your Day", "Not Signed In"),
            "signed_out": ("Sign In Again", "Signed Out"),
            "working": ("Sign Out", "Away"),
            "away": ("Back", "Away"),
            "on_break": ("End Break", "Prayer"),
        }
        for status, labels in states.items():
            state = {
                "status": status, "worked_seconds": 65, "timer_running": status in ("working", "away"),
                "signed_in_at": timezone.localtime(), "signed_out_at": timezone.localtime(),
                "break": {"reason_label": "Prayer", "note": "", "seconds": 5} if status == "on_break" else None,
            }
            html = render_to_string("workspace_attendance/workspace_card.html", {**base, "state": state})
            for label in labels:
                self.assertIn(label, html, f"{status}: {label}")
            self.assertIn("Write Today", html) if status != "on_break" else None
            if status == "working":
                self.assertNotIn("Take a Break", html)  # hidden by default (WORKSPACE_SHOW_BREAK)

    def test_break_button_comes_back_with_setting(self):
        state = {"status": "working", "worked_seconds": 1, "timer_running": True,
                 "signed_in_at": timezone.localtime(), "signed_out_at": None, "break": None}
        html = render_to_string(
            "workspace_attendance/workspace_card.html",
            {"state": state, "break_reasons": [{"value": "prayer", "label": "Prayer"}], "window_days": 30, "show_break": True},
        )
        self.assertIn("Take a Break", html)


class CardActionTests(CardTestBase):
    def test_sign_in_shows_working(self):
        response = self.post("workspace-sign-in")
        self.assertContains(response, "Working")
        self.assertContains(response, "Sign Out")
        self.assertContains(response, "Signed in at")
        self.assertTrue(Attendance.objects.filter(employee_id=self.employee).exists())

    def test_double_sign_in_keeps_one_activity(self):
        self.post("workspace-sign-in")
        response = self.post("workspace-sign-in")
        self.assertContains(response, "already signed in")
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)

    def test_sign_out(self):
        self.post("workspace-sign-in")
        response = self.post("workspace-sign-out")
        self.assertContains(response, "Signed Out")
        self.assertContains(response, "Sign In Again")
        attendance = Attendance.objects.get(employee_id=self.employee)
        self.assertIsNotNone(attendance.attendance_clock_out)

    def test_sign_out_without_sign_in_is_friendly(self):
        response = self.post("workspace-sign-out")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not signed in")

    def test_break_start_and_end(self):
        self.post("workspace-sign-in")
        response = self.post("workspace-break-start", {"reason": "prayer", "note": "short"})
        self.assertContains(response, "On Break")
        self.assertContains(response, "End Break")
        self.assertEqual(AttendanceBreak.objects.filter(employee_id=self.employee).count(), 1)
        response = self.post("workspace-break-end")
        self.assertContains(response, "Working")
        self.assertEqual(AttendanceBreak.objects.filter(employee_id=self.employee).count(), 1)

    def test_break_with_bad_reason_shows_error_in_card(self):
        self.post("workspace-sign-in")
        response = self.post("workspace-break-start", {"reason": "nonsense"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid break reason")
        self.assertContains(response, "Working")

    def test_break_without_sign_in_shows_error_in_card(self):
        response = self.post("workspace-break-start", {"reason": "prayer"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ws-note--error")

    def test_away_and_back(self):
        self.post("workspace-sign-in")
        response = self.post("workspace-away", {"away": "1"})
        self.assertContains(response, "Away")
        self.assertContains(response, "Back")
        response = self.post("workspace-away", {"away": "0"})
        self.assertContains(response, "Working")

    def test_company_rule_error_shown_in_card(self):
        from attendance.models import AttendanceGeneralSetting

        AttendanceGeneralSetting.objects.filter(company_id=self.company).update(enable_check_in=False)
        response = self.post("workspace-sign-in")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "has not been enabled")
        self.assertFalse(Attendance.objects.exists())

    def test_bad_coordinates_are_ignored(self):
        response = self.post("workspace-sign-in", {"latitude": "abc", "longitude": "999"})
        self.assertContains(response, "Working")


class FixTimesTests(CardTestBase):
    def day(self, n):
        return timezone.localdate() - timedelta(days=n)

    def test_page_lists_days_and_highlights_missing_sign_out(self):
        services.correct_times(self.employee, self.day(1), time(9, 0), None, self.user, "web")
        response = self.client.get(reverse("workspace-fix-times"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "last 30 days")
        self.assertContains(response, "overtime pay still needs HR approval")
        self.assertContains(response, "Missing sign out")
        self.assertContains(response, f'id="ws-row-{self.day(0).isoformat()}"')
        self.assertContains(response, f'id="ws-row-{self.day(30).isoformat()}"')
        html = response.content.decode()
        self.assertLess(html.index(self.day(0).isoformat()), html.index(self.day(2).isoformat()))

    def test_save_creates_logs(self):
        day = self.day(2)
        response = self.post(
            "workspace-fix-times-save",
            {"date": day.isoformat(), "sign_in": "09:00", "sign_out": "17:30"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Times saved")
        self.assertContains(response, 'value="09:00"')
        attendance = Attendance.objects.get(employee_id=self.employee, attendance_date=day)
        self.assertEqual(attendance.attendance_clock_out, time(17, 30))
        self.assertEqual(AttendanceCorrectionLog.objects.filter(employee=self.employee).count(), 3)
        self.assertTrue(AttendanceCorrectionLog.objects.filter(source="web", actor=self.user).exists())

    def test_empty_sign_out_is_allowed(self):
        day = self.day(1)
        response = self.post(
            "workspace-fix-times-save", {"date": day.isoformat(), "sign_in": "09:00", "sign_out": ""}
        )
        self.assertContains(response, "Times saved")
        self.assertContains(response, "Missing sign out")

    def test_bad_time_format_is_friendly(self):
        response = self.post(
            "workspace-fix-times-save",
            {"date": self.day(1).isoformat(), "sign_in": "9am", "sign_out": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not a valid time")
        self.assertFalse(Attendance.objects.exists())
        self.assertFalse(AttendanceCorrectionLog.objects.exists())

    def test_bad_date_is_friendly(self):
        response = self.post("workspace-fix-times-save", {"date": "nope", "sign_in": "09:00"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not valid")

    def test_empty_form_is_friendly(self):
        response = self.post("workspace-fix-times-save", {"date": self.day(1).isoformat()})
        self.assertContains(response, "Enter a sign in or sign out time")

    def test_outside_window_and_future_are_friendly(self):
        response = self.post(
            "workspace-fix-times-save", {"date": self.day(60).isoformat(), "sign_in": "09:00"}
        )
        self.assertContains(response, "contact HR")
        response = self.post(
            "workspace-fix-times-save", {"date": self.day(-2).isoformat(), "sign_in": "09:00"}
        )
        self.assertContains(response, "future")
        self.assertFalse(Attendance.objects.exists())

    def test_fix_page_for_user_without_employee(self):
        self.client.force_login(make_user("no_employee2"))
        response = self.client.get(reverse("workspace-fix-times"))
        self.assertIn(response.status_code, (200, 302))  # Horilla middleware may redirect
        self.assertNotEqual(response.status_code, 500)
