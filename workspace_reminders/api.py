"""
Reminders API for the Desktop Companion, mounted at /api/workspace/v1/reminders/.

GET returns the employee's open reminders (action still needed) plus the live
Pending Actions list; the desktop app shows each new one as a native notification.
"""

from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from workspace_attendance.api.views import WorkspaceAPIView
from workspace_reminders import conf, engine
from workspace_reminders.models import ReminderDelivery


def serialize(delivery):
    return {
        "id": delivery.pk,
        "kind": delivery.kind,
        "work_date": delivery.work_date.isoformat(),
        "message": delivery.message,
        "due_at": timezone.localtime(delivery.due_at).isoformat(),
        "created_at": timezone.localtime(delivery.created_at).isoformat(),
        "actions": {
            "sign_in": ["sign_in", "snooze"],
            "sign_in_followup": ["sign_in", "snooze"],
            "midday": ["open_update", "skip_midday", "snooze"],
            "eod": ["open_update", "snooze"],
            "sign_out": ["sign_out", "snooze"],
        }[delivery.kind],
    }


class RemindersView(WorkspaceAPIView):
    def get(self, request):
        error = self.guard()
        if error:
            return error
        open_items = engine.open_reminders(self.employee)
        ReminderDelivery.objects.filter(pk__in=[d.pk for d in open_items], desktop_seen_at__isnull=True).update(
            desktop_seen_at=timezone.now()
        )
        return Response(
            {
                "ok": True,
                "reminders": [serialize(d) for d in open_items],
                "pending_actions": engine.pending_actions(self.employee),
                "snooze_choices": conf.get()["snooze_choices"],
            }
        )


class SnoozeSerializer(serializers.Serializer):
    minutes = serializers.IntegerField()


class SnoozeView(WorkspaceAPIView):
    require_idempotency = False  # snoozing twice is harmless

    def post(self, request, delivery_id):
        error = self.guard(mutating=True)
        if error:
            return error
        data = SnoozeSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        try:
            until = engine.snooze(self.employee, delivery_id, data.validated_data["minutes"])
        except ValueError as exc:
            return Response({"ok": False, "code": "bad_minutes", "message": str(exc)}, status=400)
        if until is None:
            return Response({"ok": False, "code": "not_found", "message": "Reminder not found."}, status=404)
        return Response({"ok": True, "until": timezone.localtime(until).isoformat()})


class AckView(WorkspaceAPIView):
    require_idempotency = False

    def post(self, request, delivery_id):
        error = self.guard(mutating=True)
        if error:
            return error
        engine.acknowledge(self.employee, delivery_id)
        return Response({"ok": True})
