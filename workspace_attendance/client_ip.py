"""
The caller's IP address, read the same way as attendance.views.clock_in_out.clock_in
(X-Forwarded-For first, otherwise REMOTE_ADDR), so the office network rule gives
the same answer on the Workspace card as on the header Check-In button.
"""


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
