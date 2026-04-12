import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from routers import auth, workspaces, users, billing, tasks
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

logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Registra o webhook do Telegram na inicialização."""
    try:
        from modules.video_engine.services.telegram_bot import register_webhook
        await register_webhook(settings.base_url)
    except Exception as e:
        logger.warning(f"Não foi possível registrar webhook do Telegram: {e}")
    yield


app = FastAPI(
    title="Usina do Tempo",
    description="Plataforma SaaS de automação de vídeos para marketing digital",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(users.router)
app.include_router(billing.router)
app.include_router(negocios.router)
app.include_router(media.router)
app.include_router(pipeline.router)
app.include_router(conteudos.router)
app.include_router(videos.router)
app.include_router(telegram_webhook.router)
app.include_router(publish.router)
app.include_router(approvals.router)
app.include_router(tasks.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
