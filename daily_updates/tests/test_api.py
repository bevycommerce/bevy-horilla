"""Phase 4: Daily Updates and Reminders API."""

from datetime import datetime, time

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from daily_updates.models import DailyUpdate, DailyUpdateRevision, MiddaySkip
from workspace_attendance.tests.helpers import make_workspace_employee
from workspace_reminders import engine
from workspace_reminders.models import ReminderDelivery, ReminderSnooze

BASE = "/api/workspace/v1/"


class UpdatesRemindersAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("upd_api")
        _, _, cls.other_user, cls.other = make_workspace_employee("upd_api2", company=cls.company, shift=cls.shift)

    def client_for(self, user):
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}", HTTP_X_WORKSPACE_CLIENT="desktop")
        return c

    def test_auth_required(self):
        for path in ("updates/", "reminders/"):
            self.assertEqual(APIClient().get(BASE + path).status_code, 401)

    def test_day_state_and_submit(self):
        c = self.client_for(self.user)
        day = c.get(BASE + "updates/").json()["day"]
        self.assertTrue(day["can_submit_midday"])
        r = c.post(BASE + "updates/", {"type": "midday", "summary": "From desktop"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-000001")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(DailyUpdate.objects.get().source, "desktop")
        replay = c.post(BASE + "updates/", {"type": "midday", "summary": "From desktop"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-000001")
        self.assertTrue(replay.json()["replayed"])
        dup = c.post(BASE + "updates/", {"type": "midday", "summary": "again"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-000002")
        self.assertEqual(dup.status_code, 409)

    def test_key_required_and_validation(self):
        c = self.client_for(self.user)
        self.assertEqual(c.post(BASE + "updates/", {"type": "eod", "summary": "x"}, format="json").status_code, 400)
        bad = c.post(BASE + "updates/", {"type": "weekly", "summary": "x"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-000003")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(c.get(BASE + "updates/?date=nope").status_code, 400)

    def test_skip_and_combined(self):
        c = self.client_for(self.user)
        r = c.post(BASE + "updates/midday-skip/", {"choice": "combine"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-skip-01")
        self.assertTrue(r.json()["day"]["recommend_combined"])
        self.assertEqual(MiddaySkip.objects.get().choice, "combine")
        r = c.post(BASE + "updates/", {"type": "combined", "summary": "whole day"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-comb-01")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(DailyUpdate.objects.count(), 1)

    def test_edit_own_only(self):
        c = self.client_for(self.user)
        c.post(BASE + "updates/", {"type": "eod", "summary": "v1"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-edit-01")
        uid = DailyUpdate.objects.get().pk
        r = c.patch(BASE + f"updates/{uid}/", {"summary": "v2"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-edit-02")
        self.assertEqual(r.json()["update"]["summary"], "v2")
        other = self.client_for(self.other_user).patch(
            BASE + f"updates/{uid}/", {"summary": "hack"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-edit-03"
        )
        self.assertEqual(other.status_code, 404)

    def test_delete_removes_everything_and_allows_resend(self):
        from workspace_attendance.models import WorkspaceIdempotencyKey

        c = self.client_for(self.user)
        c.post(BASE + "updates/", {"type": "midday", "summary": "secret v1"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-del-01")
        uid = DailyUpdate.objects.get().pk
        c.patch(BASE + f"updates/{uid}/", {"summary": "secret v2"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-del-02")
        c.post(BASE + "updates/", {"type": "eod", "summary": "keep me"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-del-03")
        other = self.client_for(self.other_user).delete(BASE + f"updates/{uid}/", HTTP_IDEMPOTENCY_KEY="du-api-del-04")
        self.assertEqual(other.status_code, 404)
        self.assertEqual(c.delete(BASE + f"updates/{uid}/").status_code, 400)  # key required
        r = c.delete(BASE + f"updates/{uid}/", HTTP_IDEMPOTENCY_KEY="du-api-del-05")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(body["deleted_id"], uid)
        self.assertTrue(body["day"]["can_submit_midday"])
        self.assertIsNone(body["day"]["midday"])
        # nothing of the deleted text is kept anywhere
        self.assertFalse(DailyUpdate.objects.filter(pk=uid).exists())
        self.assertFalse(DailyUpdateRevision.objects.exists())
        for row in WorkspaceIdempotencyKey.objects.all():
            self.assertNotIn("secret", str(row.response))
        self.assertTrue(DailyUpdate.objects.filter(update_type="eod").exists())
        # a repeated delete with the same key replays; a new key says not found
        self.assertTrue(c.delete(BASE + f"updates/{uid}/", HTTP_IDEMPOTENCY_KEY="du-api-del-05").json()["replayed"])
        self.assertEqual(c.delete(BASE + f"updates/{uid}/", HTTP_IDEMPOTENCY_KEY="du-api-del-06").status_code, 404)
        # the Midday note can be sent again
        again = c.post(BASE + "updates/", {"type": "midday", "summary": "new"}, format="json", HTTP_IDEMPOTENCY_KEY="du-api-del-07")
        self.assertEqual(again.status_code, 201)

    def test_reminders_list_snooze_ack(self):
        now = timezone.make_aware(datetime.combine(timezone.localdate(), time(9, 1)))
        engine.process_employee(self.employee, now)
        c = self.client_for(self.user)
        body = c.get(BASE + "reminders/").json()
        self.assertEqual(len(body["reminders"]), 1)
        rid = body["reminders"][0]["id"]
        self.assertIn("sign_in", body["reminders"][0]["actions"])
        self.assertIsNotNone(ReminderDelivery.objects.get(pk=rid).desktop_seen_at)
        self.assertEqual(c.post(BASE + f"reminders/{rid}/snooze/", {"minutes": 45}, format="json").status_code, 400)
        self.assertEqual(c.post(BASE + f"reminders/{rid}/snooze/", {"minutes": 15}, format="json").status_code, 200)
        self.assertTrue(ReminderSnooze.objects.filter(employee=self.employee).exists())
        # someone else cannot snooze or see it
        other = self.client_for(self.other_user)
        self.assertEqual(other.post(BASE + f"reminders/{rid}/snooze/", {"minutes": 15}, format="json").status_code, 404)
        self.assertEqual(other.get(BASE + "reminders/").json()["reminders"], [])
        self.assertEqual(c.post(BASE + f"reminders/{rid}/ack/").status_code, 200)
