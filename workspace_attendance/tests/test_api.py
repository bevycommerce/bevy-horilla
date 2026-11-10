"""Phase 4 (attendance part): Workspace API security, idempotency and behaviour."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from attendance.models import Attendance, AttendanceActivity
from horilla.testkit.factories import make_user
from workspace_attendance.models import AttendanceCorrectionLog, WorkspaceAttendanceEvent

from .helpers import make_workspace_employee

BASE = "/api/workspace/v1/"


class WorkspaceAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("apiuser")
        _, _, cls.other_user, cls.other_employee = make_workspace_employee(
            "apiother", company=cls.company, shift=cls.shift
        )

    def client_for(self, user, desktop=True):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}",
            HTTP_X_WORKSPACE_CLIENT="desktop" if desktop else "",
        )
        return client

    def post(self, client, path, data=None, key="key-api-000001"):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return client.post(BASE + path, data or {}, format="json", **headers)

    def test_requires_authentication(self):
        self.assertEqual(APIClient().get(BASE + "status/").status_code, 401)
        self.assertEqual(APIClient().post(BASE + "sign-in/").status_code, 401)

    def test_expired_token_rejected(self):
        token = AccessToken.for_user(self.user)
        token.set_exp(lifetime=-timedelta(minutes=1))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(client.get(BASE + "status/").status_code, 401)

    def test_status(self):
        response = self.client_for(self.user).get(BASE + "status/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["state"]["status"], "not_signed_in")
        self.assertEqual(body["employee"]["id"], self.employee.pk)
        self.assertTrue(body["break_reasons"])
        # privacy: the card holds only the approved fields
        self.assertEqual(set(body["employee"]), {"id", "name", "photo", "department", "job_position"})

    def test_user_without_employee(self):
        lonely = make_user("lonely_api")
        response = self.client_for(lonely).get(BASE + "status/")
        # Horilla's token authentication already refuses accounts without a
        # company/employee (403); if that ever changes, the Workspace guard does.
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attendance.objects.exists())

    def test_idempotency_key_required(self):
        response = self.post(self.client_for(self.user), "sign-in/", key=None)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Attendance.objects.exists())

    def test_sign_in_retry_and_sign_out(self):
        client = self.client_for(self.user)
        first = self.post(client, "sign-in/", key="key-api-signin-1")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["state"]["status"], "working")
        retry = self.post(client, "sign-in/", key="key-api-signin-1")
        self.assertTrue(retry.json()["replayed"])
        self.assertEqual(AttendanceActivity.objects.filter(employee_id=self.employee).count(), 1)
        self.assertEqual(WorkspaceAttendanceEvent.objects.get(action="sign_in").source, "desktop")

        out = self.post(client, "sign-out/", key="key-api-signout-1")
        self.assertEqual(out.json()["state"]["status"], "signed_out")
        self.assertTrue(Attendance.objects.get(employee_id=self.employee).attendance_validated)

    def test_client_cannot_act_for_another_employee(self):
        client = self.client_for(self.user)
        self.post(client, "sign-in/", {"employee_id": self.other_employee.pk, "employee": self.other_employee.pk})
        self.assertTrue(Attendance.objects.filter(employee_id=self.employee).exists())
        self.assertFalse(Attendance.objects.filter(employee_id=self.other_employee).exists())

    def test_source_is_api_without_desktop_header(self):
        self.post(self.client_for(self.user, desktop=False), "sign-in/", key="key-api-src-01")
        self.assertEqual(WorkspaceAttendanceEvent.objects.get(action="sign_in").source, "api")

    def test_break_validation_and_flow(self):
        client = self.client_for(self.user)
        self.post(client, "sign-in/", key="key-api-brk-00")
        bad = self.post(client, "break/start/", {"reason": "nap"}, key="key-api-brk-01")
        self.assertEqual(bad.status_code, 400)
        ok = self.post(client, "break/start/", {"reason": "prayer", "note": "x"}, key="key-api-brk-02")
        self.assertEqual(ok.json()["state"]["status"], "on_break")
        end = self.post(client, "break/end/", key="key-api-brk-03")
        self.assertEqual(end.json()["state"]["status"], "working")

    def test_away_requires_sign_in(self):
        response = self.post(self.client_for(self.user), "away/", {"away": True}, key="key-api-away-1")
        self.assertEqual(response.status_code, 409)

    def test_corrections(self):
        client = self.client_for(self.user)
        day = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.post(client, "corrections/", {"date": day, "sign_in": "09:00", "sign_out": "17:00"}, key="key-api-fix-01")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(AttendanceCorrectionLog.objects.filter(employee=self.employee).count(), 3)
        listing = client.get(BASE + "corrections/").json()
        row = next(d for d in listing["days"] if d["date"] == day)
        self.assertEqual((row["sign_in"], row["sign_out"]), ("09:00", "17:00"))

    def test_correction_validation_errors(self):
        client = self.client_for(self.user)
        self.assertEqual(self.post(client, "corrections/", {"date": "not-a-date"}, key="key-api-fix-02").status_code, 400)
        old = (timezone.localdate() - timedelta(days=60)).isoformat()
        response = self.post(client, "corrections/", {"date": old, "sign_in": "09:00"}, key="key-api-fix-03")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "outside_window")
