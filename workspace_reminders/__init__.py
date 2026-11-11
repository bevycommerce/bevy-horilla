"""
Smart Employee Workspace: reminder engine.

One idempotent APScheduler job decides, per employee and per shift, which
reminder is due. Every delivery is recorded first (unique per employee, day,
kind and attempt), so restarts or a second scheduler can never double-send.
"""
