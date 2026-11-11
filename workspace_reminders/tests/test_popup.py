"""Portal Midday popup: shows when due, close hides it until the next hour, actions work."""

from datetime import datetime, time
from unittest import mock

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from daily_updates.models import DailyUpdate, MiddaySkip
from workspace_attendance import services as ws
from workspace_attendance.tests.helpers import make_workspace_employee
from workspace_reminders import engine
from workspace_reminders.models import ReminderDelivery

HX = {"HTTP_HX_REQUEST": "true"}


def at(hour, minute=0):
    return timezone.make_aware(datetime.combine(timezone.localdate(), time(hour, minute)))


class MiddayPopupTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("popup_emp")

    def setUp(self):
        self.client.force_login(self.user)
        ws.correct_times(self.employee, timezone.localdate(), time(9, 0), None, self.user, "web")

    def make_due(self):
        delivered = engine.process_employee(self.employee, at(13, 1))
        return [d for d in delivered if d.kind == "midday"][0]

    def get_popup(self):
        return self.client.get(reverse("ws-midday-popup"), **HX)

    def test_nothing_before_due(self):
        self.assertEqual(self.get_popup().content, b"")

    def test_popup_shows_when_due(self):
        self.make_due()
        html = self.get_popup().content.decode()
        self.assertIn("Time for your Midday update", html)
        self.assertIn("Skip Midday", html)
        self.assertIn("Sign Out", html)
        self.assertNotIn("Late", html)

    def test_close_hides_until_next_hour(self):
        delivery = self.make_due()
        self.client.post(reverse("ws-midday-popup-close", args=[delivery.pk]), **HX)
        self.assertEqual(self.get_popup().content, b"")
        engine.process_employee(self.employee, at(14, 2))
        self.assertIn("Time for your Midday update", self.get_popup().content.decode())

    def test_submit_midday(self):
        delivery = self.make_due()
        html = self.client.post(
            reverse("ws-midday-popup-submit", args=[delivery.pk]), {"summary": "Fixed bugs"}, **HX
        ).content.decode()
        self.assertIn("Midday update sent", html)
        self.assertEqual(DailyUpdate.objects.get().summary, "Fixed bugs")
        self.assertEqual(self.get_popup().content, b"")

    def test_empty_note_shows_error(self):
        delivery = self.make_due()
        html = self.client.post(reverse("ws-midday-popup-submit", args=[delivery.pk]), {"summary": " "}, **HX).content.decode()
        self.assertIn("Please write a short note", html)
        self.assertFalse(DailyUpdate.objects.exists())

    def test_skip_combine(self):
        delivery = self.make_due()
        self.client.post(reverse("ws-midday-popup-skip", args=[delivery.pk]), **HX)
        self.assertEqual(MiddaySkip.objects.get().choice, MiddaySkip.COMBINE)
        self.assertFalse(DailyUpdate.objects.exists())
        self.assertEqual(self.get_popup().content, b"")

    def test_sign_out_from_popup(self):
        delivery = self.make_due()
        with mock.patch("workspace_attendance.adapters.horilla.HorillaAdapter.check_allowed"):
            self.client.post(reverse("ws-midday-popup-sign-out", args=[delivery.pk]), **HX)
        self.assertEqual(ws.get_state(self.employee)["status"], "signed_out")
        self.assertEqual(self.get_popup().content, b"")

    def test_cannot_act_on_someone_elses_popup(self):
        delivery = self.make_due()
        other_user = make_workspace_employee("popup_other", company=self.company, shift=self.shift)[2]
        self.client.force_login(other_user)
        self.client.post(reverse("ws-midday-popup-submit", args=[delivery.pk]), {"summary": "x"}, **HX)
        self.client.post(reverse("ws-midday-popup-close", args=[delivery.pk]), **HX)
        self.assertFalse(DailyUpdate.objects.exists())
        self.assertIsNone(ReminderDelivery.objects.get(pk=delivery.pk).acknowledged_at)
