"""Backward-compatibility wrapper — canonical location: modules.video_engine.services.notifier"""
from modules.video_engine.services.notifier import *  # noqa: F401,F403
from modules.video_engine.services.notifier import (  # noqa: F401
    notify_approval_needed,
    notify_published,
    notify_error,
)
