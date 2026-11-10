"""Company-wide feed and Today board: visibility, filters and privacy."""

import json
from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone

from base.models import Department
from daily_updates import services
from daily_updates.models import EOD, MIDDAY, MiddaySkip
from employee.models import EmployeeWorkInformation
from workspace_attendance import services as ws
from workspace_attendance.tests.helpers import make_workspace_employee


class CompanyViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user_a, cls.alice = make_workspace_employee("alice_cv")
        _, _, cls.user_b, cls.bob = make_workspace_employee("bob_cv", company=cls.company, shift=cls.shift)
        cls.eng = Department.objects.create(department="Engineering")
        cls.ops = Department.objects.create(department="Operations")
        EmployeeWorkInformation.objects.filter(employee_id=cls.alice).update(department_id=cls.eng)
        EmployeeWorkInformation.objects.filter(employee_id=cls.bob).update(department_id=cls.ops)
        # sensitive values that must never appear in shared output
        EmployeeWorkInformation.objects.filter(employee_id=cls.alice).update(basic_salary=987654)
        cls.alice.phone = "5550001112"
        cls.alice.save()

    def setUp(self):
        self.today = timezone.localdate()
        services.submit_update(self.alice, self.today, MIDDAY, {"summary": "Alice midday", "blockers": "API down"}, "web")
        services.submit_update(self.bob, self.today, EOD, {"summary": "Bob eod"}, "web")
        services.skip_midday(self.bob, self.today, MiddaySkip.LATER, "web")

    def test_everyone_sees_everyones_updates(self):
        feed = services.company_feed(self.today, self.today)
        names = {row["employee"]["name"] for row in feed}
        self.assertEqual(len(feed), 2)
        self.assertTrue(any("Alice midday" == row["update"]["summary"] for row in feed))
        self.assertTrue(any("API down" == row["update"]["blockers"] for row in feed))
        self.assertEqual(len(names), 2)

    def test_filters(self):
        self.assertEqual(len(services.company_feed(self.today, self.today, update_type=EOD)), 1)
        self.assertEqual(len(services.company_feed(self.today, self.today, department_id=self.eng.pk)), 1)
        by_name = services.company_feed(self.today, self.today, query=self.bob.employee_first_name)
        self.assertTrue(all(r["employee"]["id"] == self.bob.pk for r in by_name))
        old = self.today - timedelta(days=3)
        self.assertEqual(services.company_feed(old, old), [])

    def test_privacy_no_sensitive_fields(self):
        feed = services.company_feed(self.today, self.today)
        board = services.today_board(self.today)
        blob = json.dumps({"feed": feed, "board": board}, default=str)
        for secret in (self.alice.email, "5550001112", "987654", "basic_salary", "phone", "email"):
            self.assertNotIn(secret, blob)
        self.assertEqual(
            set(feed[0]["employee"]), {"id", "name", "photo", "department_id", "department", "job_position"}
        )

    def test_today_board(self):
        ws.sign_in(self.alice, "web")
        board = services.today_board(self.today)
        self.assertEqual(board["employee_count"], 2)
        self.assertEqual(board["totals"]["working"], 1)
        self.assertEqual(board["totals"]["updates"], 2)
        bob_row = next(r for r in board["rows"] if r["employee"]["id"] == self.bob.pk)
        self.assertEqual(bob_row["midday_skip"], MiddaySkip.LATER)
        self.assertIn("eod", bob_row["updates"])

    def test_missing_sign_out_flag_for_yesterday(self):
        yesterday = self.today - timedelta(days=1)
        ws.correct_times(self.alice, yesterday, time(9, 0), None, self.user_a, "web")
        board = services.today_board(yesterday)
        alice_row = next(r for r in board["rows"] if r["employee"]["id"] == self.alice.pk)
        self.assertIn("sign_out", alice_row["missing"])
