"""Backward-compatibility wrapper — canonical location: core.config"""
from core.config import *  # noqa: F401,F403
from core.config import get_settings  # noqa: F401 — explicit re-export
