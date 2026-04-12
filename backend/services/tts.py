"""Backward-compatibility wrapper — canonical location: modules.video_engine.services.tts"""
from modules.video_engine.services.tts import *  # noqa: F401,F403
from modules.video_engine.services.tts import (  # noqa: F401
    PIPELINE_TMP_DIR,
    ensure_pipeline_dir,
    generate_audio,
    get_default_voice,
)
