"""
Daily Updates API for the Desktop Companion, mounted at /api/workspace/v1/updates/.
Same auth, ownership and Idempotency-Key rules as the attendance API.
"""

from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response

from daily_updates import services
from daily_updates.models import COMBINED, EOD, MIDDAY, MiddaySkip
from workspace_attendance.api.views import WorkspaceAPIView


class UpdateSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    type = serializers.ChoiceField(choices=[MIDDAY, EOD, COMBINED])
    summary = serializers.CharField(max_length=5000, allow_blank=True)
    completed = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")
    ongoing = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")
    blockers = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")


class EditSerializer(serializers.Serializer):
    summary = serializers.CharField(max_length=5000, allow_blank=True)
    completed = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")
    ongoing = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")
    blockers = serializers.CharField(max_length=3000, required=False, allow_blank=True, default="")


class SkipSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    choice = serializers.ChoiceField(choices=[MiddaySkip.LATER, MiddaySkip.COMBINE])


class DayView(WorkspaceAPIView):
    """GET: what exists for a day and what can still be sent. POST: send an update."""

    def get(self, request):
        error = self.guard()
        if error:
            return error
        raw = request.query_params.get("date")
        try:
            day = serializers.DateField().to_internal_value(raw) if raw else timezone.localdate()
        except serializers.ValidationError:
            return Response({"ok": False, "code": "bad_date", "message": "Invalid date."}, status=400)
        return Response({"ok": True, "day": services.serialize_day(services.day_state(self.employee, day))})

    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        data = UpdateSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        fields = {k: v.get(k, "") for k in ("summary", "completed", "ongoing", "blockers")}
        return self.respond(
            services.submit_update(
                self.employee, v.get("date") or timezone.localdate(), v["type"], fields, self.source, key=self.idempotency_key()
            )
        )


class EditView(WorkspaceAPIView):
    def patch(self, request, update_id):
        error = self.guard(mutating=True)
        if error:
            return error
        data = EditSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self.respond(
            services.edit_update(
                self.employee, update_id, dict(data.validated_data), self.source, request.user, key=self.idempotency_key()
            )
        )

    def delete(self, request, update_id):
        error = self.guard(mutating=True)
        if error:
            return error
        return self.respond(
            services.delete_update(self.employee, update_id, self.source, key=self.idempotency_key())
        )


class SkipView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        data = SkipSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        return self.respond(
            services.skip_midday(
                self.employee, v.get("date") or timezone.localdate(), v["choice"], self.source, key=self.idempotency_key()
            )
        )
