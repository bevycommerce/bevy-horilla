"""The reporting manager set in the HR portal is always one of the leave approvers."""

from django.test import TestCase

from base.models import Department, JobPosition
from leave.approvals import (
    DIRECTOR_POSITION,
    HR_LEAD_POSITION,
    PRODUCT_MANAGER_POSITION,
    determine_approvers,
)
from workspace_attendance.tests.helpers import make_workspace_employee


class ReportingManagerApproverTests(TestCase):
    def setUp(self):
        self.company, self.shift, _, self.emp = make_workspace_employee("rm_emp")
        _, _, _, self.manager = make_workspace_employee("rm_mgr", company=self.company, shift=self.shift)
        _, _, _, self.hr = make_workspace_employee("rm_hr", company=self.company, shift=self.shift)
        _, _, _, self.director = make_workspace_employee("rm_dir", company=self.company, shift=self.shift)
        self.dept = Department.objects.create(department="Ops")
        self.set_position(self.hr, HR_LEAD_POSITION)
        self.set_position(self.director, DIRECTOR_POSITION)

    def set_position(self, employee, name):
        position, _ = JobPosition.objects.get_or_create(job_position=name, department_id=self.dept)
        info = employee.employee_work_info
        info.job_position_id = position
        info.save()

    def set_manager(self, employee, manager):
        info = employee.employee_work_info
        info.reporting_manager_id = manager
        info.save()

    def approvers(self, employee):
        employee.refresh_from_db()
        return {person.id: reasons for person, reasons in determine_approvers(employee)}

    def test_reporting_manager_and_hr_lead_for_a_normal_employee(self):
        self.set_manager(self.emp, self.manager)
        found = self.approvers(self.emp)
        self.assertIn("Reporting Manager", found[self.manager.id])
        self.assertIn(HR_LEAD_POSITION, found[self.hr.id])

    def test_product_manager_also_gets_their_reporting_manager(self):
        self.set_position(self.emp, PRODUCT_MANAGER_POSITION)
        self.set_manager(self.emp, self.manager)
        found = self.approvers(self.emp)
        self.assertIn("Reporting Manager", found[self.manager.id])
        self.assertIn(DIRECTOR_POSITION, found[self.director.id])
        self.assertIn(HR_LEAD_POSITION, found[self.hr.id])

    def test_manager_who_is_also_hr_lead_is_listed_once_with_both_reasons(self):
        self.set_manager(self.emp, self.hr)
        found = self.approvers(self.emp)
        self.assertEqual(sorted(found[self.hr.id]), sorted(["Reporting Manager", HR_LEAD_POSITION]))

    def test_no_reporting_manager_or_inactive_manager_is_fine(self):
        self.assertNotIn(self.manager.id, self.approvers(self.emp))
        self.set_manager(self.emp, self.manager)
        self.manager.is_active = False
        self.manager.save()
        self.assertNotIn(self.manager.id, self.approvers(self.emp))

    def test_employee_is_never_their_own_approver(self):
        self.set_manager(self.emp, self.emp)
        self.assertNotIn(self.emp.id, self.approvers(self.emp))
