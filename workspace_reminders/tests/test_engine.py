"""Phase 3 tests: shift-based reminders, stop rules, snooze, day-off exclusions, duplicates."""

import threading
from datetime import datetime, time, timedelta

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from notifications.models import Notification

from base.models import Holidays
from daily_updates import services as updates
from daily_updates.models import EOD, MIDDAY, MiddaySkip
from horilla.testkit.factories import make_leave_request, make_leave_type
from workspace_attendance import services as ws
from workspace_attendance.tests.helpers import make_workspace_employee
from workspace_reminders import engine
from workspace_reminders.models import ReminderDelivery, ReminderSnooze


def at(hour, minute=0, day=None):
    day = day or timezone.localdate()
    return timezone.make_aware(datetime.combine(day, time(hour, minute)))


def kinds(employee):
    return sorted(ReminderDelivery.objects.filter(employee=employee).values_list("kind", "attempt"))


class ReminderEngineTests(TestCase):
    """Shift 09:00-18:00: sign_in 09:00, follow-up 09:30, midday 13:30 (+14:00), eod 17:30 (+18:00), sign_out 18:00 (+18:30)."""

    @classmethod
    def setUpTestData(cls):
        cls.company, cls.shift, cls.user, cls.employee = make_workspace_employee("reminded")

    def run_at(self, hour, minute=0):
        return engine.process_employee(self.employee, at(hour, minute))

    def test_nothing_before_shift(self):
        self.assertEqual(self.run_at(8, 30), [])

    def test_sign_in_reminder_once(self):
        self.assertEqual(len(self.run_at(9, 1)), 1)
        self.assertEqual(self.run_at(9, 3), [])
        self.assertEqual(kinds(self.employee), [("sign_in", 1)])
        delivery = ReminderDelivery.objects.get()
        self.assertTrue(delivery.portal_notified)
        self.assertEqual(Notification.objects.filter(recipient=self.employee.employee_user_id).count(), 1)

    def test_follow_up_if_still_missing(self):
        self.run_at(9, 1)
        self.run_at(9, 31)
        self.assertEqual(kinds(self.employee), [("sign_in", 1), ("sign_in_followup", 1)])

    def test_no_sign_in_reminder_after_signing_in(self):
        ws.sign_in(self.employee, "web")
        engine.process_employee(self.employee, timezone.localtime().replace(hour=9, minute=31))
        self.assertFalse(ReminderDelivery.objects.filter(kind__startswith="sign_in").exists())

    def test_stale_reminders_are_not_sent(self):
        self.run_at(11, 0)
        self.assertFalse(ReminderDelivery.objects.filter(kind__startswith="sign_in").exists())

    def test_midday_repeats_then_stops_after_submit(self):
        self.run_at(13, 31)
        self.run_at(14, 1)
        self.assertEqual(
            [k for k in kinds(self.employee) if k[0] == "midday"], [("midday", 1), ("midday", 2)]
        )
        updates.submit_update(self.employee, timezone.localdate(), MIDDAY, {"summary": "done"}, "web")
        self.assertFalse(engine.needs(self.employee, timezone.localdate(), at(14, 5))["midday"])

    def test_skip_midday_stops_only_midday(self):
        updates.skip_midday(self.employee, timezone.localdate(), MiddaySkip.COMBINE, "web")
        self.run_at(13, 31)
        self.run_at(17, 31)
        got = kinds(self.employee)
        self.assertNotIn(("midday", 1), got)
        self.assertIn(("eod", 1), got)

    def test_eod_stops_after_combined_or_eod(self):
        updates.submit_update(self.employee, timezone.localdate(), EOD, {"summary": "eod"}, "web")
        self.run_at(17, 31)
        self.assertNotIn(("eod", 1), kinds(self.employee))

    def test_sign_out_reminder_only_while_working(self):
        self.run_at(18, 1)
        self.assertNotIn(("sign_out", 1), kinds(self.employee))
        ws.sign_in(self.employee, "web")
        state = ws.get_state(self.employee)
        self.assertEqual(state["status"], "working")
        engine.process_employee(self.employee, at(18, 1, day=state["work_date"]))
        self.assertIn(("sign_out", 1), kinds(self.employee))

    def test_snooze(self):
        delivery = self.run_at(13, 31)[0]
        self.assertEqual(delivery.kind, "midday")
        until = engine.snooze(self.employee, delivery.pk, 15)
        self.assertIsNotNone(ReminderDelivery.objects.get(pk=delivery.pk).acknowledged_at)
        ReminderSnooze.objects.update(until=at(13, 46))
        self.run_at(13, 40)
        self.assertEqual([k for k in kinds(self.employee) if k[0] == "midday"], [("midday", 1)])
        self.run_at(13, 47)
        self.assertIn(("midday", 101), kinds(self.employee))
        # the scheduled 14:00 repeat is replaced by the snooze re-fire
        self.run_at(14, 1)
        self.assertNotIn(("midday", 2), kinds(self.employee))
        self.assertIsNotNone(until)

    def test_snooze_only_15_or_30(self):
        delivery = self.run_at(9, 1)[0]
        with self.assertRaises(ValueError):
            engine.snooze(self.employee, delivery.pk, 45)

    def test_snooze_someone_elses_reminder_does_nothing(self):
        other = make_workspace_employee("snoozer2", company=self.company, shift=self.shift)[3]
        delivery = self.run_at(9, 1)[0]
        self.assertIsNone(engine.snooze(other, delivery.pk, 15))
        self.assertFalse(ReminderSnooze.objects.exists())

    def test_holiday_means_no_reminders(self):
        Holidays.objects.create(name="Victory Day", start_date=timezone.localdate(), end_date=timezone.localdate())
        self.assertEqual(self.run_at(9, 1), [])

    def test_approved_leave_means_no_reminders(self):
        leave_type = make_leave_type()
        make_leave_request(
            employee=self.employee, leave_type=leave_type,
            start_date=timezone.localdate(), end_date=timezone.localdate(), status="approved",
        )
        self.assertEqual(self.run_at(9, 1), [])

    def test_requested_leave_still_gets_reminders(self):
        leave_type = make_leave_type("Casual")
        make_leave_request(
            employee=self.employee, leave_type=leave_type,
            start_date=timezone.localdate(), end_date=timezone.localdate(), status="requested",
        )
        self.assertEqual(len(self.run_at(9, 1)), 1)

    def test_open_reminders_hide_done_actions(self):
        self.run_at(9, 1)
        self.assertEqual(len(engine.open_reminders(self.employee, at(9, 2))), 1)
        ws.correct_times(self.employee, timezone.localdate(), time(8, 55), None, self.user, "web")
        self.assertEqual(engine.open_reminders(self.employee, at(9, 3)), [])

    def test_pending_actions(self):
        actions = engine.pending_actions(self.employee, at(14, 0))
        self.assertEqual([a["kind"] for a in actions], ["sign_in", "midday"])
        yesterday = timezone.localdate() - timedelta(days=1)
        ws.correct_times(self.employee, yesterday, time(9, 0), None, self.user, "web")
        actions = engine.pending_actions(self.employee, at(8, 0))
        self.assertIn("fix_sign_out", [a["kind"] for a in actions])

    def test_run_reminders_is_idempotent(self):
        engine.run_reminders(now=at(9, 1))
        engine.run_reminders(now=at(9, 1))
        self.assertEqual(ReminderDelivery.objects.filter(employee=self.employee).count(), 1)

    def test_disabled_by_setting(self):
        with self.settings(WORKSPACE_REMINDERS={"enabled": False}):
            self.assertEqual(engine.run_reminders(now=at(9, 1)), 0)


class DuplicateSchedulerTests(TransactionTestCase):
    """Two scheduler processes running the job at the same moment send each reminder once."""

    def setUp(self):
        self.company, self.shift, self.user, self.employee = make_workspace_employee("dupsched")

    def test_parallel_runs(self):
        barrier = threading.Barrier(2)
        errors = []

        def job():
            try:
                barrier.wait()
                engine.run_reminders(now=at(9, 1))
            except Exception as error:  # pragma: no cover
                errors.append(error)
            finally:
                connection.close()

        threads = [threading.Thread(target=job) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(ReminderDelivery.objects.filter(employee=self.employee).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.employee.employee_user_id).count(), 1)
