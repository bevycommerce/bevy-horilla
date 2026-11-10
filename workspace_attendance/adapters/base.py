"""
The contract between the Smart Workspace modules and the host HR system.

To move the Workspace into another Django HR portal, write a new class with
these methods and point settings.WORKSPACE_ADAPTER at it. Nothing else in
workspace_attendance, daily_updates or workspace_reminders imports HR models.
"""


class AttendanceActionError(Exception):
    """An attendance action that cannot be done. args[0] is a message safe to show."""

    def __init__(self, message, code="invalid"):
        super().__init__(message)
        self.code = code


class BaseAdapter:
    # --- people -------------------------------------------------------
    def get_employee(self, user):
        """The employee linked to a user, or None."""
        raise NotImplementedError

    def safe_employee_card(self, employee):
        """Only the fields everyone in the company may see: id, name, photo, department, job position."""
        raise NotImplementedError

    # --- attendance state ---------------------------------------------
    def get_state(self, employee, now=None):
        """dict: status, work_date, signed_in_at, signed_out_at, worked_seconds, break, away_since."""
        raise NotImplementedError

    def attendance_by_day(self, employee, start, end):
        """{date: {"sign_in": time|None, "sign_out": time|None, "worked": "HH:MM"}}."""
        raise NotImplementedError

    def break_reasons(self):
        """[{"value": ..., "label": ...}] for the break menu."""
        raise NotImplementedError

    def check_allowed(self, employee, client_ip=None, coords=None):
        """Raise AttendanceActionError when the company rules block a sign in/out (disabled, IP, location)."""
        raise NotImplementedError

    # --- attendance actions -------------------------------------------
    def sign_in(self, employee, now):
        raise NotImplementedError

    def sign_out(self, employee, now):
        raise NotImplementedError

    def start_break(self, employee, reason, note, now):
        raise NotImplementedError

    def end_break(self, employee, now):
        raise NotImplementedError

    def set_away(self, employee, now):
        raise NotImplementedError

    def clear_away(self, employee):
        raise NotImplementedError

    def correct_times(self, employee, work_date, sign_in, sign_out, now):
        """Return (attendance, changes) where changes is a list of (field, old, new)."""
        raise NotImplementedError

    def mark_valid_for_payroll(self, attendance):
        raise NotImplementedError

    # --- schedule and notifications (used by reminders) ---------------
    def is_day_off(self, employee, day):
        """True on holidays, company leave days and approved leave."""
        raise NotImplementedError

    def notify(self, employee, message, url=None):
        """Put a message in the portal notification centre."""
        raise NotImplementedError

    def shift_window(self, employee, day):
        """(start_datetime, end_datetime) of the employee's shift on that day, or None when off."""
        raise NotImplementedError
