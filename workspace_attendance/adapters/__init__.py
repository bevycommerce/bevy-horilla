"""Adapter loading. The adapter is the only place that imports the host HR system's models."""

from django.utils.module_loading import import_string

from workspace_attendance import conf

_adapter = None


def get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = import_string(conf.get("WORKSPACE_ADAPTER"))()
    return _adapter
