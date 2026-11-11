"""Daily Updates web pages: my page, actions, company dashboard and privacy."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from base.models import Department
from daily_updates import services
from daily_updates.models import COMBINED, EOD, MIDDAY, DailyUpdate, DailyUpdateRevision, MiddaySkip
from employee.models import EmployeeWorkInformation
from workspace_attendance.tests.helpers import make_workspace_employee

HX = {"HTTP_HX_REQUEST": "true"}
SALARY = 987654
PHONE = "5550001112"


class ViewBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.me = make_workspace_employee("du_me")
        _, _, cls.other_user, cls.other = make_workspace_employee("du_other", company=cls.company, shift=cls.shift)
        cls.dept = Department.objects.create(department="Engineering")
        EmployeeWorkInformation.objects.filter(employee_id=cls.other).update(
            department_id=cls.dept, basic_salary=SALARY
        )
        cls.other.phone = PHONE
        cls.other.save()

    def setUp(self):
        self.client.force_login(self.user)
        self.today = timezone.localdate()

    def day(self, date=None):
        return services.day_state(self.me, date or self.today)

    def submit(self, update_type, summary="Did things", date=None, **extra):
        data = {"type": update_type, "summary": summary, "date": (date or self.today).isoformat(), **extra}
        return self.client.post(reverse("daily-updates-submit"), data, **HX)


class MyPageTests(ViewBase):
    def test_page_renders(self):
        response = self.client.get(reverse("daily-updates"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What are you working on?")
        self.assertContains(response, "Add details (optional)")
        self.assertContains(response, "Skip Midday")
        self.assertContains(response, "Write Midday note later")
        self.assertContains(response, "Combine with End of Day")
        self.assertContains(response, "never blocks Sign Out")
        self.assertContains(response, "visible to everyone in the company")
        self.assertContains(response, self.today.strftime("%d %b %Y"))

    def test_unauthenticated_redirects(self):
        self.client.logout()
        for name in ("daily-updates", "daily-updates-company", "daily-updates-company-tab"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn("login", response["Location"])
        response = self.client.post(reverse("daily-updates-submit"), {"type": "eod", "summary": "x"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DailyUpdate.objects.exists())

    def test_actions_refuse_get(self):
        for name in ("daily-updates-submit", "daily-updates-skip"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 405)

    def test_submit_midday(self):
        response = self.submit(MIDDAY, "Working on the report", ongoing="Charts")
        self.assertContains(response, "Update sent.")
        update = DailyUpdate.objects.get(employee=self.me)
        self.assertEqual((update.update_type, update.summary, update.ongoing), (MIDDAY, "Working on the report", "Charts"))
        # midday form is gone, EOD form still there, carry-forward button offered
        self.assertNotContains(response, "What are you working on?")
        self.assertContains(response, "Submit End of Day")
        self.assertContains(response, "Copy unfinished items")
        self.assertContains(response, "Submitted")

    def test_carry_forward_button_only_with_ongoing_items(self):
        response = self.submit(MIDDAY, "No ongoing")
        self.assertNotContains(response, "Copy unfinished items")

    def test_skip_later_shows_late_editor(self):
        response = self.client.post(
            reverse("daily-updates-skip"), {"choice": "later", "date": self.today.isoformat()}, **HX
        )
        self.assertContains(response, "Midday skipped")
        self.assertContains(response, "Your Midday note")
        self.assertNotContains(response, "marked late")
        self.assertNotContains(response, "Skip Midday")
        self.assertEqual(MiddaySkip.objects.get(employee=self.me).choice, MiddaySkip.LATER)
        self.assertFalse(DailyUpdate.objects.exists())
        response = self.submit(MIDDAY, "Late midday")
        self.assertTrue(DailyUpdate.objects.get(employee=self.me).is_late)
        # owner rule: no "late" labels anywhere in the interface
        self.assertNotContains(response, ">Late<")

    def test_skip_combine_then_combined_via_view(self):
        response = self.client.post(
            reverse("daily-updates-skip"), {"choice": "combine", "date": self.today.isoformat()}, **HX
        )
        self.assertContains(response, "Write your whole day in one note")
        self.assertContains(response, "Use the regular End-of-Day form instead")
        response = self.submit(COMBINED, "All day long")
        self.assertContains(response, "Update sent.")
        self.assertEqual(DailyUpdate.objects.filter(employee=self.me).count(), 1)
        self.assertEqual(DailyUpdate.objects.get(employee=self.me).update_type, COMBINED)
        self.assertNotContains(response, "Submit End of Day")
        self.assertNotContains(response, "Submit combined note")

    def test_regular_eod_link_shows_regular_form(self):
        services.skip_midday(self.me, self.today, MiddaySkip.COMBINE, "web")
        response = self.client.get(
            reverse("daily-updates"), {"part": "day", "date": self.today.isoformat(), "regular": "1"}, **HX
        )
        self.assertContains(response, "Submit End of Day")
        self.assertNotContains(response, "<html")

    def test_duplicate_submit_shows_friendly_error(self):
        self.submit(EOD, "First")
        response = self.submit(EOD, "Second")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already sent")
        self.assertEqual(DailyUpdate.objects.filter(employee=self.me).count(), 1)

    def test_empty_note_keeps_typed_details(self):
        response = self.submit(EOD, "   ", completed="Kept text")
        self.assertContains(response, "Please write a short note")
        self.assertContains(response, "Kept text")
        self.assertFalse(DailyUpdate.objects.exists())

    def test_bad_type_is_friendly(self):
        response = self.submit("nonsense")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unknown update type")

    def test_edit_creates_revision_and_shows_edited(self):
        self.submit(EOD, "Original")
        update = DailyUpdate.objects.get(employee=self.me)
        response = self.client.post(
            reverse("daily-updates-edit", args=[update.pk]),
            {"summary": "Changed", "date": self.today.isoformat()},
            **HX,
        )
        self.assertContains(response, "Update saved.")
        self.assertContains(response, "Edited")
        self.assertContains(response, "Changed")
        update.refresh_from_db()
        self.assertEqual(update.summary, "Changed")
        revision = DailyUpdateRevision.objects.get(update=update)
        self.assertEqual(revision.summary, "Original")

    def test_cannot_edit_someone_elses_update(self):
        services.submit_update(self.other, self.today, EOD, {"summary": "Theirs"}, "web")
        theirs = DailyUpdate.objects.get(employee=self.other)
        response = self.client.post(
            reverse("daily-updates-edit", args=[theirs.pk]), {"summary": "Hacked", "date": self.today.isoformat()}, **HX
        )
        self.assertContains(response, "Update not found")
        theirs.refresh_from_db()
        self.assertEqual(theirs.summary, "Theirs")

    def test_history_lists_versions_for_anyone(self):
        self.submit(EOD, "Version one")
        update = DailyUpdate.objects.get(employee=self.me)
        services.edit_update(self.me, update.pk, {"summary": "Version two"}, "web", actor=self.user)
        self.client.force_login(self.other_user)
        response = self.client.get(reverse("daily-updates-history", args=[update.pk]), **HX)
        self.assertContains(response, "Version one")
        self.assertContains(response, "Version two")
        self.assertContains(response, "Current version")
        full = self.client.get(reverse("daily-updates-history", args=[update.pk]))
        self.assertContains(full, "Version one")

    def test_history_missing_update_is_friendly(self):
        response = self.client.get(reverse("daily-updates-history", args=[999999]), **HX)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Update not found")
        self.assertEqual(self.client.get(reverse("daily-updates-history", args=[999999])).status_code, 404)

    def test_backdated_day_and_badge(self):
        day = self.today - timedelta(days=2)
        response = self.client.get(reverse("daily-updates"), {"date": day.isoformat()})
        self.assertContains(response, day.strftime("%d %b %Y"))
        self.assertContains(response, "Backdated")
        response = self.submit(EOD, "Late note", date=day)
        update = DailyUpdate.objects.get(employee=self.me)
        self.assertEqual(update.work_date, day)
        self.assertTrue(update.is_backdated)
        self.assertContains(response, "Backdated")

    def test_bad_date_input_is_friendly(self):
        response = self.client.get(reverse("daily-updates"), {"date": "not-a-date"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not a valid date")
        response = self.client.post(
            reverse("daily-updates-submit"), {"type": EOD, "summary": "x", "date": "31/02/2026"}, **HX
        )
        self.assertContains(response, "not a valid date")
        self.assertFalse(DailyUpdate.objects.exists())

    def test_future_date_refused(self):
        future = self.today + timedelta(days=2)
        response = self.client.get(reverse("daily-updates"), {"date": future.isoformat()})
        self.assertContains(response, "future day")
        response = self.submit(EOD, "Early", date=future)
        self.assertContains(response, "future day")
        self.assertFalse(DailyUpdate.objects.exists())

    def test_too_old_date_refused_by_service(self):
        old = self.today - timedelta(days=services.backdate_days() + 5)
        response = self.submit(EOD, "Ancient", date=old)
        self.assertContains(response, "last %s days" % services.backdate_days())
        self.assertFalse(DailyUpdate.objects.exists())

    def test_recent_list_only_shows_my_updates_last_14_days(self):
        services.submit_update(self.other, self.today, EOD, {"summary": "Other person text"}, "web")
        services.submit_update(self.me, self.today - timedelta(days=3), EOD, {"summary": "Recent mine"}, "web")
        services.submit_update(self.me, self.today - timedelta(days=20), EOD, {"summary": "Too old to list"}, "web")
        response = self.client.get(reverse("daily-updates"))
        self.assertContains(response, "Recent mine")
        self.assertNotContains(response, "Too old to list")
        self.assertNotContains(response, "Other person text")


class CompanyTests(ViewBase):
    def setUp(self):
        super().setUp()
        services.submit_update(self.other, self.today, MIDDAY, {"summary": "Other midday text", "blockers": "Waiting on API"}, "web")
        services.submit_update(self.me, self.today, EOD, {"summary": "My eod text"}, "web")
        services.skip_midday(self.me, self.today - timedelta(days=1), MiddaySkip.LATER, "web")

    def tab(self, name, **params):
        return self.client.get(reverse("daily-updates-company-tab"), {"tab": name, **params}, **HX)

    def test_company_page_renders_with_notice_and_tabs(self):
        response = self.client.get(reverse("daily-updates-company"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "visible to everyone in the company")
        for label in ("Today", "Attendance", "Work Updates", "History"):
            self.assertContains(response, label)

    def test_today_tab_shows_tiles_and_others_updates(self):
        response = self.tab("today")
        for label in ("Working", "On break", "Signed out", "Not signed in", "Updates today"):
            self.assertContains(response, label)
        for label in (">Late<", "Missing actions", "No sign in", "No sign out"):
            self.assertNotContains(response, label)
        self.assertContains(response, "Other midday text")
        self.assertContains(response, "Waiting on API")
        self.assertContains(response, "My eod text")
        self.assertContains(response, "Engineering")
        self.assertIn("daily-updates/company/?tab=today", response["HX-Push-Url"])

    def test_today_tab_shows_skip_note(self):
        # the other person already sent a Midday note, so use a third person-free check on me:
        # my EOD exists, so "later" is the allowed skip
        services.skip_midday(self.me, self.today, MiddaySkip.LATER, "web")
        response = self.tab("today")
        self.assertContains(response, "Midday skipped (will write later)")

    def test_attendance_tab_renders(self):
        response = self.tab("attendance")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No sign in")

    def test_work_updates_tab_shows_separate_dates(self):
        response = self.tab("updates")
        self.assertContains(response, "Work date")
        self.assertContains(response, "Submitted")
        self.assertContains(response, "Other midday text")

    def test_history_tab_default_last_7_days(self):
        old = self.today - timedelta(days=5)
        services.submit_update(self.other, old, EOD, {"summary": "Five days ago text"}, "web")
        response = self.tab("history")
        self.assertContains(response, "Five days ago text")
        self.assertContains(response, "Other midday text")
        older = self.today - timedelta(days=12)
        services.submit_update(self.other, older, EOD, {"summary": "Twelve days ago text"}, "web")
        self.assertNotContains(self.tab("history"), "Twelve days ago text")
        wide = self.tab("history", **{"from": older.isoformat(), "to": self.today.isoformat()})
        self.assertContains(wide, "Twelve days ago text")

    def test_filters(self):
        response = self.tab("updates", q=self.other.employee_first_name)
        self.assertContains(response, "Other midday text")
        self.assertNotContains(response, "My eod text")
        response = self.tab("updates", dept=str(self.dept.pk))
        self.assertContains(response, "Other midday text")
        self.assertNotContains(response, "My eod text")
        response = self.tab("updates", type=EOD)
        self.assertContains(response, "My eod text")
        self.assertNotContains(response, "Other midday text")
        response = self.tab("today", type=EOD)
        self.assertContains(response, "My eod text")
        self.assertNotContains(response, "Other midday text")

    def test_bad_filters_are_friendly(self):
        response = self.tab("updates", **{"from": "garbage"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not a valid date")
        response = self.tab("today", date=(self.today + timedelta(days=3)).isoformat())
        self.assertContains(response, "cannot be in the future")
        response = self.tab("updates", **{"from": self.today.isoformat(), "to": (self.today - timedelta(days=2)).isoformat()})
        self.assertContains(response, "after the To date")
        response = self.tab("nonsense", dept="abc", type="zzz")
        self.assertEqual(response.status_code, 200)

    def test_work_updates_tab_marks_edited_with_history_button(self):
        update = DailyUpdate.objects.get(employee=self.other)
        services.edit_update(self.other, update.pk, {"summary": "Changed midday"}, "web", actor=self.other_user)
        response = self.tab("updates")
        self.assertContains(response, "Edited")
        self.assertContains(response, reverse("daily-updates-history", args=[update.pk]))

    def test_privacy_no_email_phone_or_salary_on_any_tab(self):
        pages = [self.client.get(reverse("daily-updates-company")), self.client.get(reverse("daily-updates"))]
        for name in ("today", "attendance", "updates", "history"):
            pages.append(self.tab(name))
            pages.append(self.tab(name, q=self.other.employee_first_name))
        update = DailyUpdate.objects.get(employee=self.other)
        pages.append(self.client.get(reverse("daily-updates-history", args=[update.pk]), **HX))
        pages.append(self.client.get(reverse("daily-updates-history", args=[update.pk])))
        for response in pages:
            html = response.content.decode()
            self.assertNotIn("du_other@test.horilla", html)
            self.assertNotIn(PHONE, html)
            self.assertNotIn(str(SALARY), html)
            self.assertNotIn("987,654", html)
        # the employee card itself is shown
        self.assertContains(self.tab("today"), self.other.get_full_name())
