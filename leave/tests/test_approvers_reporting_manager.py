"""
Leave approvers (owner rules 2026-11-13): reporting manager + HR Lead always,
plus the PMs of the employee's projects from the approvers Google Sheet.
If the sheet cannot be used or the employee is not in it, HR Lead is told why.
"""

from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from base.models import Department, JobPosition
from leave import approver_sheet
from leave.approvals import HR_LEAD_POSITION, determine_approvers_with_status
from workspace_attendance.tests.helpers import make_workspace_employee

HEAD = ["Project Name", "Emails", "Developer/Software Engineer", "PM/PMs"]


class ParseTests(SimpleTestCase):
    def test_columns_found_by_heading_and_cells_split(self):
        rows = [HEAD, ["Careers site", "dev1@x.com, dev2@x.com", "Rafi Ahmed", "pm1@x.com\npm2@x.com"], []]
        projects = approver_sheet.parse_rows(rows)
        self.assertEqual(len(projects), 1)
        p = projects[0]
        self.assertEqual(p["project"], "Careers site")
        self.assertIn(("email", "dev2@x.com"), p["members"])
        self.assertIn(("name", "rafi ahmed"), p["members"])
        self.assertEqual(p["pms"], [("email", "pm1@x.com"), ("email", "pm2@x.com")])

    def test_project_manager_heading_also_works(self):
        projects = approver_sheet.parse_rows([["Project", "Developers", "Project Manager"], ["A", "d@x.com", "Nadia Islam"]])
        self.assertEqual(projects[0]["pms"], [("name", "nadia islam")])

    def test_no_pm_column_or_empty_sheet_is_reported(self):
        with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "no PM column"):
            approver_sheet.parse_rows([["Project", "Emails"], ["A", "d@x.com"]])
        with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "empty"):
            approver_sheet.parse_rows([])

    def test_not_set_up(self):
        with self.settings(LEAVE_APPROVER_SHEET_ID="", LEAVE_APPROVER_SHEET_KEY_FILE=""), mock.patch.dict("os.environ", {}, clear=False):
            with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "not set up"):
                approver_sheet._fetch_rows()


class ApproverRulesTests(TestCase):
    def setUp(self):
        cache.clear()
        self.company, self.shift, _, self.emp = make_workspace_employee("ap_emp")
        make = lambda u: make_workspace_employee(u, company=self.company, shift=self.shift)[3]
        self.manager, self.hr, self.pm1, self.pm2 = make("ap_mgr"), make("ap_hr"), make("ap_pm1"), make("ap_pm2")
        for e, mail in ((self.emp, "emp@bevy.test"), (self.pm1, "pm1@bevy.test"), (self.pm2, "pm2@bevy.test")):
            e.email = mail
            e.save()
        self.pm2.employee_first_name, self.pm2.employee_last_name = "Nadia", "Islam"
        self.pm2.save()
        dept = Department.objects.create(department="Ops")
        position, _ = JobPosition.objects.get_or_create(job_position=HR_LEAD_POSITION, department_id=dept)
        info = self.hr.employee_work_info
        info.job_position_id = position
        info.save()
        info = self.emp.employee_work_info
        info.reporting_manager_id = self.manager
        info.save()
        self.emp.refresh_from_db()

    def run_with(self, rows=None, error=None):
        def fake():
            if error:
                raise approver_sheet.SheetUnavailable(error)
            return rows
        with mock.patch.object(approver_sheet, "_fetch_rows", side_effect=fake):
            cache.clear()
            approvers, problems = determine_approvers_with_status(self.emp)
        return {p.id: r for p, r in approvers}, problems

    def test_sheet_pms_plus_reporting_manager_plus_hr_lead(self):
        found, problems = self.run_with([HEAD, ["Careers", "emp@bevy.test", "", "pm1@bevy.test, Nadia Islam"], ["Other", "x@y.z", "", "nobody@bevy.test"]])
        self.assertEqual(problems, [])
        self.assertEqual(found[self.manager.id], ["Reporting Manager"])
        self.assertEqual(found[self.hr.id], [HR_LEAD_POSITION])
        self.assertEqual(found[self.pm1.id], ["PM of Careers"])
        self.assertEqual(found[self.pm2.id], ["PM of Careers"])

    def test_two_projects_with_the_same_pm_listed_once_with_both_reasons(self):
        found, _ = self.run_with([HEAD, ["A", "emp@bevy.test", "", "pm1@bevy.test"], ["B", "", "EMP@bevy.test", "pm1@bevy.test"]])
        self.assertEqual(found[self.pm1.id], ["PM of A", "PM of B"])

    def test_sheet_unreachable_gives_reporting_manager_and_hr_lead_with_reason(self):
        found, problems = self.run_with(error="the approvers sheet could not be reached")
        self.assertEqual(set(found), {self.manager.id, self.hr.id})
        self.assertEqual(problems, ["the approvers sheet could not be reached"])

    def test_employee_not_in_sheet(self):
        found, problems = self.run_with([HEAD, ["A", "someone@else.com", "", "pm1@bevy.test"]])
        self.assertEqual(set(found), {self.manager.id, self.hr.id})
        self.assertIn("not found in the approvers sheet", problems[0])

    def test_unknown_pm_is_reported_but_others_still_added(self):
        found, problems = self.run_with([HEAD, ["A", "emp@bevy.test", "", "pm1@bevy.test, ghost@bevy.test"]])
        self.assertIn(self.pm1.id, found)
        self.assertIn("ghost@bevy.test", problems[0])

    def test_hr_lead_is_told_when_something_is_missing(self):
        from leave import approvals

        leave_request = mock.Mock(status="requested", employee_id=self.emp)
        request = mock.Mock()
        request.user.employee_get = self.emp
        with mock.patch.object(approver_sheet, "_fetch_rows", side_effect=approver_sheet.SheetUnavailable("the approvers sheet could not be reached")), \
             mock.patch.object(approvals, "notify") as notify, \
             mock.patch.object(approvals.LeaveApprover.objects, "get_or_create", return_value=(None, False)):
            cache.clear()
            approvals.create_approver_rows(request, leave_request)
        verbs = [c.kwargs["verb"] for c in notify.send.call_args_list]
        self.assertTrue(any("could not be reached" in v and "Proper approvers could not be added" in v for v in verbs))
        recipients = [c.kwargs["recipient"] for c in notify.send.call_args_list]
        self.assertIn(self.hr.employee_user_id, recipients)

    def test_employee_never_approves_own_leave(self):
        info = self.emp.employee_work_info
        info.reporting_manager_id = self.emp
        info.save()
        self.emp.refresh_from_db()
        found, _ = self.run_with([HEAD, ["A", "emp@bevy.test", "", "emp@bevy.test"]])
        self.assertNotIn(self.emp.id, found)


class FetchTests(SimpleTestCase):
    def fetch(self, status, payload=None):
        response = mock.Mock(status_code=status)
        response.json.return_value = payload or {}
        with self.settings(LEAVE_APPROVER_SHEET_ID="abc", LEAVE_APPROVER_SHEET_KEY_FILE=__file__), \
             mock.patch("google.oauth2.service_account.Credentials.from_service_account_file"), \
             mock.patch("google.auth.transport.requests.AuthorizedSession") as session:
            session.return_value.get.return_value = response
            return approver_sheet._fetch_rows()

    def test_ok(self):
        self.assertEqual(self.fetch(200, {"values": [HEAD]}), [HEAD])

    def test_not_shared_and_not_found(self):
        with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "not shared"):
            self.fetch(403)
        with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "not found"):
            self.fetch(404)

    def test_missing_key_file(self):
        with self.settings(LEAVE_APPROVER_SHEET_ID="abc", LEAVE_APPROVER_SHEET_KEY_FILE="/nope/key.json"):
            with self.assertRaisesMessage(approver_sheet.SheetUnavailable, "key file"):
                approver_sheet._fetch_rows()
