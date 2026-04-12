"""Backward-compatibility wrapper — canonical location: core.auth"""
from core.auth import *  # noqa: F401,F403
from core.auth import (  # noqa: F401 — explicit re-exports
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_invite_token,
    decode_token,
    get_current_user,
    require_role,
)
