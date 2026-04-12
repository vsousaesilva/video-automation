"""
Routers do módulo video_engine.
Reexporta todos os routers para facilitar o registro no main.py.
"""

from modules.video_engine.routers import (
    apps,
    media,
    pipeline,
    conteudos,
    videos,
    publish,
    approvals,
    telegram_webhook,
)

all_routers = [
    apps.router,
    media.router,
    pipeline.router,
    conteudos.router,
    videos.router,
    publish.router,
    approvals.router,
    telegram_webhook.router,
]
