"""Phase 2 tests: Midday / Skip / Write later / Combine / EOD / edits."""

from datetime import timedelta
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone

from daily_updates import services
from daily_updates.models import COMBINED, EOD, MIDDAY, DailyUpdate, DailyUpdateRevision, MiddaySkip
from workspace_attendance.services import WorkspaceError
from workspace_attendance.tests.helpers import make_workspace_employee


def note(text="Worked on the login page", **extra):
    return {"summary": text, **extra}


class DailyUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("updater")

    def setUp(self):
        self.today = timezone.localdate()

    # -------------------------------------------------- midday
    def test_midday_submit(self):
        status, body = services.submit_update(
            self.employee, self.today, MIDDAY, note(completed="A", ongoing="B", blockers="C"), "web"
        )
        self.assertEqual(status, 201)
        update = DailyUpdate.objects.get()
        self.assertEqual((update.update_type, update.completed, update.ongoing, update.blockers), (MIDDAY, "A", "B", "C"))
        self.assertEqual(update.work_date, self.today)
        self.assertIsNotNone(update.submitted_at)
        self.assertFalse(body["day"]["can_submit_midday"])
        self.assertTrue(body["day"]["can_submit_eod"])
        self.assertFalse(body["day"]["can_submit_combined"])

    def test_midday_needs_a_note(self):
        with self.assertRaises(WorkspaceError):
            services.submit_update(self.employee, self.today, MIDDAY, {"summary": "   "}, "web")
        self.assertFalse(DailyUpdate.objects.exists())

    def test_duplicate_midday_refused(self):
        services.submit_update(self.employee, self.today, MIDDAY, note(), "web")
        with self.assertRaises(WorkspaceError) as ctx:
            services.submit_update(self.employee, self.today, MIDDAY, note("again"), "desktop")
        self.assertEqual(ctx.exception.code, "duplicate")
        self.assertEqual(DailyUpdate.objects.count(), 1)

    def test_same_key_replays_instead_of_duplicating(self):
        services.submit_update(self.employee, self.today, EOD, note(), "desktop", key="upd-key-00001")
        status, body = services.submit_update(self.employee, self.today, EOD, note(), "desktop", key="upd-key-00001")
        self.assertTrue(body["replayed"])
        self.assertEqual(DailyUpdate.objects.count(), 1)

    # -------------------------------------------------- skip: write later
    def test_skip_later_creates_no_update(self):
        status, body = services.skip_midday(self.employee, self.today, MiddaySkip.LATER, "web")
        self.assertFalse(DailyUpdate.objects.exists())
        self.assertTrue(body["day"]["midday_pending_later"])
        self.assertTrue(body["day"]["can_submit_midday"])
        self.assertTrue(body["day"]["can_submit_eod"])

    def test_write_later_then_submit_is_marked_late(self):
        services.skip_midday(self.employee, self.today, MiddaySkip.LATER, "web")
        services.submit_update(self.employee, self.today, MIDDAY, note("late midday"), "web")
        update = DailyUpdate.objects.get(update_type=MIDDAY)
        self.assertTrue(update.is_late)
        # EOD can still follow separately
        services.submit_update(self.employee, self.today, EOD, note("eod"), "web")
        self.assertEqual(DailyUpdate.objects.count(), 2)

    def test_pending_midday_does_not_expire_after_the_day(self):
        yesterday = self.today - timedelta(days=1)
        services.skip_midday(self.employee, yesterday, MiddaySkip.LATER, "web")
        services.submit_update(self.employee, yesterday, MIDDAY, note("written next morning"), "web")
        update = DailyUpdate.objects.get()
        self.assertEqual(update.work_date, yesterday)
        self.assertTrue(update.is_late)
        self.assertTrue(update.is_backdated)

    # -------------------------------------------------- skip: combine
    def test_combine_flow_saves_one_record(self):
        status, body = services.skip_midday(self.employee, self.today, MiddaySkip.COMBINE, "web")
        self.assertTrue(body["day"]["recommend_combined"])
        services.submit_update(self.employee, self.today, COMBINED, note("whole day"), "web")
        self.assertEqual(DailyUpdate.objects.count(), 1)
        self.assertEqual(DailyUpdate.objects.get().update_type, COMBINED)
        state = services.day_state(self.employee, self.today)
        self.assertFalse(state["can_submit_midday"])
        self.assertFalse(state["can_submit_eod"])
        self.assertFalse(state["can_submit_combined"])

    def test_combined_blocks_separate_updates(self):
        services.submit_update(self.employee, self.today, COMBINED, note(), "web")
        for kind in (MIDDAY, EOD):
            with self.assertRaises(WorkspaceError) as ctx:
                services.submit_update(self.employee, self.today, kind, note(), "web")
            self.assertEqual(ctx.exception.code, "combined_exists")
        self.assertEqual(DailyUpdate.objects.count(), 1)

    def test_separate_update_blocks_combined(self):
        services.submit_update(self.employee, self.today, MIDDAY, note(), "web")
        with self.assertRaises(WorkspaceError) as ctx:
            services.submit_update(self.employee, self.today, COMBINED, note(), "web")
        self.assertEqual(ctx.exception.code, "separate_exists")

    def test_skip_after_midday_sent_refused(self):
        services.submit_update(self.employee, self.today, MIDDAY, note(), "web")
        with self.assertRaises(WorkspaceError):
            services.skip_midday(self.employee, self.today, MiddaySkip.LATER, "web")

    def test_combine_choice_after_eod_refused(self):
        services.submit_update(self.employee, self.today, EOD, note(), "web")
        with self.assertRaises(WorkspaceError) as ctx:
            services.skip_midday(self.employee, self.today, MiddaySkip.COMBINE, "web")
        self.assertEqual(ctx.exception.code, "eod_exists")

    def test_skip_choice_can_change(self):
        services.skip_midday(self.employee, self.today, MiddaySkip.LATER, "web")
        services.skip_midday(self.employee, self.today, MiddaySkip.COMBINE, "web")
        self.assertEqual(MiddaySkip.objects.get().choice, MiddaySkip.COMBINE)
        self.assertEqual(MiddaySkip.objects.count(), 1)

    # -------------------------------------------------- eod
    def test_regular_eod_and_carry_forward(self):
        services.submit_update(self.employee, self.today, MIDDAY, note(ongoing="Finish API tests"), "web")
        state = services.day_state(self.employee, self.today)
        self.assertEqual(state["carry_forward"], "Finish API tests")
        services.submit_update(self.employee, self.today, EOD, note("done"), "web")
        # carry forward is offered, never copied automatically
        self.assertEqual(DailyUpdate.objects.get(update_type=EOD).ongoing, "")

    def test_eod_for_past_day_is_late_and_backdated(self):
        day = self.today - timedelta(days=2)
        services.submit_update(self.employee, day, EOD, note(), "web")
        update = DailyUpdate.objects.get()
        self.assertTrue(update.is_late)
        self.assertTrue(update.is_backdated)

    def test_future_and_too_old_refused(self):
        with self.assertRaises(WorkspaceError):
            services.submit_update(self.employee, self.today + timedelta(days=1), EOD, note(), "web")
        with self.assertRaises(WorkspaceError):
            services.submit_update(self.employee, self.today - timedelta(days=31), EOD, note(), "web")

    @override_settings(WORKSPACE_UPDATE_BACKDATE_DAYS=3)
    def test_backdate_window_configurable(self):
        with self.assertRaises(WorkspaceError):
            services.submit_update(self.employee, self.today - timedelta(days=4), EOD, note(), "web")

    def test_midday_on_time_vs_late_by_shift(self):
        # shift 09:00-18:00 -> midpoint 13:30 + 60 min grace = 14:30
        noon = timezone.make_aware(timezone.datetime.combine(self.today, timezone.datetime.min.time())) + timedelta(hours=12)
        with mock.patch("daily_updates.services.timezone.localtime", return_value=noon):
            services.submit_update(self.employee, self.today, MIDDAY, note(), "web")
        self.assertFalse(DailyUpdate.objects.get().is_late)
        other = make_workspace_employee("updater_late", company=self.company, shift=self.shift)[3]
        evening = noon + timedelta(hours=5)
        with mock.patch("daily_updates.services.timezone.localtime", return_value=evening):
            services.submit_update(other, self.today, MIDDAY, note(), "web")
        self.assertTrue(DailyUpdate.objects.get(employee=other).is_late)

    # -------------------------------------------------- edits
    def test_edit_keeps_history(self):
        services.submit_update(self.employee, self.today, EOD, note("first"), "web")
        update = DailyUpdate.objects.get()
        services.edit_update(self.employee, update.pk, note("second"), "web", self.user)
        services.edit_update(self.employee, update.pk, note("third"), "desktop", self.user)
        update.refresh_from_db()
        self.assertEqual(update.summary, "third")
        self.assertTrue(update.is_edited)
        self.assertEqual(update.revision_count, 2)
        self.assertEqual(list(update.revisions.values_list("summary", flat=True)), ["second", "first"])
        history = services.update_history(update)
        self.assertEqual(history[0]["revision"], 2)

    def test_edit_with_no_change_creates_no_revision(self):
        services.submit_update(self.employee, self.today, EOD, note("same"), "web")
        update = DailyUpdate.objects.get()
        services.edit_update(self.employee, update.pk, note("same"), "web", self.user)
        self.assertEqual(DailyUpdateRevision.objects.count(), 0)

    def test_cannot_edit_someone_elses_update(self):
        other = make_workspace_employee("intruder", company=self.company, shift=self.shift)[3]
        services.submit_update(self.employee, self.today, EOD, note("mine"), "web")
        update = DailyUpdate.objects.get()
        with self.assertRaises(WorkspaceError) as ctx:
            services.edit_update(other, update.pk, note("hacked"), "web", self.user)
        self.assertEqual(ctx.exception.status, 404)
        update.refresh_from_db()
        self.assertEqual(update.summary, "mine")

    def test_revision_rows_are_immutable(self):
        services.submit_update(self.employee, self.today, EOD, note("v1"), "web")
        update = DailyUpdate.objects.get()
        services.edit_update(self.employee, update.pk, note("v2"), "web", self.user)
        revision = update.revisions.first()
        revision.summary = "rewritten"
        with self.assertRaises(ValueError):
            revision.save()
