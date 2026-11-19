"""
Break Log CSV export.
"""

import csv
import io
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from attendance.models import AttendanceBreak
from workspace_attendance.tests.helpers import make_workspace_employee


def read_csv(response):
    text = (
        b"".join(response.streaming_content).decode()
        if response.streaming
        else response.content.decode()
    )
    return list(csv.reader(io.StringIO(text.lstrip("﻿"))))


class BreakLogExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee(
            "brk_me"
        )
        _, _, cls.other_user, cls.other = make_workspace_employee(
            "brk_other", company=cls.company, shift=cls.shift
        )
        now = timezone.now()
        today = timezone.localdate()
        AttendanceBreak.objects.create(
            employee_id=cls.employee,
            attendance_date=today,
            reason="prayer",
            note='=HYPERLINK("x")',
            start_datetime=now - timedelta(minutes=20),
            end_datetime=now - timedelta(minutes=5),
        )
        AttendanceBreak.objects.create(
            employee_id=cls.employee,
            attendance_date=date(2024, 1, 15),
            reason="technical_issue",
            note="old one",
            start_datetime=now - timedelta(days=600),
            end_datetime=now - timedelta(days=600) + timedelta(minutes=10),
        )
        AttendanceBreak.objects.create(
            employee_id=cls.other,
            attendance_date=today,
            reason="prayer",
            note="someone else",
            start_datetime=now - timedelta(minutes=30),
        )

    def setUp(self):
        self.client.force_login(self.user)

    def test_page_has_export_buttons_and_note_column(self):
        response = self.client.get(reverse("break-log-view"))
        self.assertContains(response, "Export CSV")
        self.assertContains(response, "Export All (CSV)")
        self.assertContains(response, "Note")

    def test_export_uses_the_chosen_dates_and_only_own_breaks(self):
        today = timezone.localdate().isoformat()
        response = self.client.get(
            reverse("break-log-view"), {"from": today, "to": today, "export": "csv"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn(
            f"break-log_{today}_to_{today}.csv", response["Content-Disposition"]
        )
        rows = read_csv(response)
        self.assertEqual(rows[0][:4], ["Employee", "Date", "Reason", "Note"])
        self.assertEqual(len(rows), 2)  # header + my one break today
        self.assertNotIn("someone else", str(rows))
        self.assertEqual(rows[1][3], '\'=HYPERLINK("x")')  # never runs as a formula
        self.assertEqual(rows[1][7], "Ended")

    def test_export_all_includes_every_date(self):
        response = self.client.get(
            reverse("break-log-view"), {"export": "csv", "all": "1"}
        )
        rows = read_csv(response)
        self.assertIn("break-log_all.csv", response["Content-Disposition"])
        notes = [r[3] for r in rows[1:]]
        self.assertIn("old one", notes)
        self.assertNotIn("someone else", notes)

    def test_admin_export_includes_everyone(self):
        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(
            reverse("break-log-view"), {"export": "csv", "all": "1"}
        )
        notes = [r[3] for r in read_csv(response)[1:]]
        self.assertIn("someone else", notes)
        running = [
            r
            for r in read_csv(
                self.client.get(
                    reverse("break-log-view"), {"export": "csv", "all": "1"}
                )
            )[1:]
            if r[3] == "someone else"
        ][0]
        self.assertEqual(running[7], "Running")
        self.assertEqual(running[5], "")
