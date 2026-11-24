"""
Smart Workspace attendance API, used by the Desktop Companion.

Authentication: the existing Horilla JWT (POST /api/auth/login/), same as the
mobile app. The employee is always the logged-in user; the client can never
choose whose attendance it changes. Every POST needs an Idempotency-Key header
so a retried request (e.g. after a network drop) is applied only once.
"""

from rest_framework import status as http
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from attendance.methods.utils import get_client_ip
from workspace_attendance import conf, services
from workspace_attendance.adapters import get_adapter

from .serializers import AwaySerializer, BreakStartSerializer, CoordsSerializer, CorrectionSerializer


def _error(message, code, status_code):
    return Response({"ok": False, "code": code, "message": str(message)}, status=status_code)


class WorkspaceAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = None
    require_idempotency = True

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self.employee = get_adapter().get_employee(request.user)

    def handle_exception(self, exc):
        if isinstance(exc, services.WorkspaceError):
            return _error(exc.message, exc.code, exc.status)
        return super().handle_exception(exc)

    @property
    def source(self):
        client = (self.request.headers.get("X-Workspace-Client") or "").lower()
        return "desktop" if client == "desktop" else "api"

    def idempotency_key(self):
        return (self.request.headers.get("Idempotency-Key") or "").strip()

    def guard(self, mutating=False):
        """Common checks. Returns an error Response or None."""
        if self.employee is None:
            return _error("Your account is not linked to an employee profile.", "no_employee", http.HTTP_403_FORBIDDEN)
        if mutating and self.require_idempotency and not self.idempotency_key():
            return _error("The Idempotency-Key header is required.", "idempotency_required", http.HTTP_400_BAD_REQUEST)
        return None

    def coords(self):
        data = CoordsSerializer(data=self.request.data)
        data.is_valid(raise_exception=True)
        return {k: v for k, v in data.validated_data.items() if v is not None}

    def respond(self, result):
        status_code, body = result
        return Response(body, status=status_code)


class StatusView(WorkspaceAPIView):
    def get(self, request):
        error = self.guard()
        if error:
            return error
        adapter = get_adapter()
        return Response(
            {
                "ok": True,
                "employee": adapter.safe_employee_card(self.employee),
                "state": services.serialize_state(services.get_state(self.employee)),
                "break_reasons": adapter.break_reasons(),
                "correction_window_days": conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS"),
            }
        )


class SignInView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        return self.respond(
            services.sign_in(
                self.employee, self.source, client_ip=get_client_ip(request), coords=self.coords(), key=self.idempotency_key()
            )
        )


class SignOutView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        return self.respond(
            services.sign_out(
                self.employee, self.source, client_ip=get_client_ip(request), coords=self.coords(), key=self.idempotency_key()
            )
        )


class BreakStartView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        data = BreakStartSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self.respond(
            services.start_break(
                self.employee, data.validated_data["reason"], data.validated_data["note"], self.source, key=self.idempotency_key()
            )
        )


class BreakEndView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        return self.respond(services.end_break(self.employee, self.source, key=self.idempotency_key()))


class AwayView(WorkspaceAPIView):
    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        data = AwaySerializer(data=request.data)
        data.is_valid(raise_exception=True)
        return self.respond(
            services.set_away(self.employee, data.validated_data["away"], self.source, key=self.idempotency_key())
        )


class CorrectionsView(WorkspaceAPIView):
    def get(self, request):
        error = self.guard()
        if error:
            return error
        days = services.recent_days(self.employee)
        return Response(
            {
                "ok": True,
                "window_days": conf.get("WORKSPACE_CORRECTION_WINDOW_DAYS"),
                "days": [
                    {
                        "date": d["date"].isoformat(),
                        "sign_in": d["sign_in"].strftime("%H:%M") if d["sign_in"] else None,
                        "sign_out": d["sign_out"].strftime("%H:%M") if d["sign_out"] else None,
                        "worked": d["worked"],
                        "missing_sign_out": d["missing_sign_out"],
                    }
                    for d in days
                ],
            }
        )

    def post(self, request):
        error = self.guard(mutating=True)
        if error:
            return error
        data = CorrectionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        return self.respond(
            services.correct_times(
                self.employee, v["date"], v["sign_in"], v["sign_out"], request.user, self.source, key=self.idempotency_key()
            )
        )
