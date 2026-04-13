import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import get_settings
from core.rate_limit import limiter, rate_limit_exceeded_handler
from core.middleware import (
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
    BillingEnforcementMiddleware,
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routers import auth, workspaces, users, billing, tasks, privacy
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
    version="0.2.0",
    lifespan=lifespan,
)

# === Rate Limiting (SlowAPI) ===
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# === CORS restritivo ===
allowed_origins = [
    "https://app.usinadotempo.com.br",
    "https://usinadotempo.com.br",
    "https://www.usinadotempo.com.br",
]
# Em dev, incluir também a URL local do frontend
if settings.frontend_url and settings.frontend_url not in allowed_origins:
    allowed_origins.append(settings.frontend_url)

# === Middlewares ===
# Starlette executa na ordem INVERSA de adição (último add = primeiro a rodar).
# CORS deve ser o ÚLTIMO adicionado para interceptar OPTIONS preflight primeiro.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(BillingEnforcementMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# === Routers ===
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(users.router)
app.include_router(billing.router)
app.include_router(privacy.router)
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
    return {"status": "ok", "version": "0.2.0"}
