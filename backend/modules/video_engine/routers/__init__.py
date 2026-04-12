"""
Routers do módulo video_engine.
Reexporta todos os routers para facilitar o registro no main.py.
"""

from modules.video_engine.routers import (
    negocios,
    media,
    pipeline,
    conteudos,
    videos,
    publish,
    approvals,
    telegram_webhook,
)

all_routers = [
    negocios.router,
    media.router,
    pipeline.router,
    conteudos.router,
    videos.router,
    publish.router,
    approvals.router,
    telegram_webhook.router,
]
