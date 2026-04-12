"""Backward-compatibility wrapper — canonical location: core.db"""
from core.db import *  # noqa: F401,F403
from core.db import get_supabase  # noqa: F401 — explicit re-export
