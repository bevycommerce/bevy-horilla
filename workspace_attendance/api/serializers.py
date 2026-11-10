"""Input validation for the Workspace API. Output is the plain dict built by services."""

from rest_framework import serializers

from workspace_attendance.adapters import get_adapter


class CoordsSerializer(serializers.Serializer):
    latitude = serializers.FloatField(required=False, min_value=-90, max_value=90)
    longitude = serializers.FloatField(required=False, min_value=-180, max_value=180)


class BreakStartSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=30)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")

    def validate_reason(self, value):
        allowed = {item["value"] for item in get_adapter().break_reasons()}
        if value not in allowed:
            raise serializers.ValidationError("Unknown break reason.")
        return value


class AwaySerializer(serializers.Serializer):
    away = serializers.BooleanField()


class CorrectionSerializer(serializers.Serializer):
    date = serializers.DateField()
    sign_in = serializers.TimeField(required=False, allow_null=True, default=None, input_formats=["%H:%M", "%H:%M:%S"])
    sign_out = serializers.TimeField(required=False, allow_null=True, default=None, input_formats=["%H:%M", "%H:%M:%S"])

    def validate(self, attrs):
        if attrs.get("sign_in") is None and attrs.get("sign_out") is None:
            raise serializers.ValidationError("Enter a sign in or sign out time.")
        return attrs
