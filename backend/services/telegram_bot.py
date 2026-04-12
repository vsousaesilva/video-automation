"""Backward-compatibility wrapper — canonical location: modules.video_engine.services.telegram_bot"""
from modules.video_engine.services.telegram_bot import *  # noqa: F401,F403
from modules.video_engine.services.telegram_bot import (  # noqa: F401
    TELEGRAM_API,
    send_approval_request,
    send_published_notification,
    send_error_notification,
    update_telegram_message,
    register_webhook,
)
