"""Backward-compatibility wrapper — canonical location: modules.video_engine.services.video_validator"""
from modules.video_engine.services.video_validator import *  # noqa: F401,F403
from modules.video_engine.services.video_validator import (  # noqa: F401
    validate_video,
    update_video_status_error,
    update_video_status_approved,
    _log_etapa,
)
