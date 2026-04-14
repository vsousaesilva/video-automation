import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.auth import get_current_user
from core.config import get_settings
from core.rate_limit import limiter, rate_limit_exceeded_handler
from core.middleware import (
    SecurityHeadersMiddleware,
    AuditLogMiddleware,
    BillingEnforcementMiddleware,
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from routers import admin, auth, workspaces, users, billing, tasks, privacy
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
from modules.dashboard import router as dashboard_router
from modules.content_ai import router as content_ai_router
from modules.crm import router as crm_router
from modules.ads_manager import router as ads_manager_router

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
    version="0.7.0",
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
app.include_router(admin.router)
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
app.include_router(dashboard_router.router)
app.include_router(content_ai_router.router)
app.include_router(crm_router.router)
app.include_router(ads_manager_router.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.7.0"}


@app.get("/debug/my-context")
async def debug_my_context(
    current_user: dict = Depends(get_current_user),
):
    """Endpoint de diagnóstico — mostra user, workspace, negocios, conteudos e videos."""
    from core.db import get_supabase

    supabase = get_supabase()
    user_id = current_user["id"]
    workspace_id = current_user.get("workspace_id")

    # Negocios do workspace
    negocios = []
    neg_ids = []
    if workspace_id:
        neg_result = (
            supabase.table("negocios")
            .select("id, nome, status, workspace_id")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        negocios = neg_result.data or []
        neg_ids = [n["id"] for n in negocios]

    # Conteudos dos negocios
    conteudos = []
    if neg_ids:
        cont_result = (
            supabase.table("conteudos")
            .select("id, negocio_id, tipo_conteudo, status, erro_msg, criado_em")
            .in_("negocio_id", neg_ids)
            .order("criado_em", desc=True)
            .limit(20)
            .execute()
        )
        conteudos = cont_result.data or []

    # Videos dos negocios
    videos = []
    if neg_ids:
        vid_result = (
            supabase.table("videos")
            .select("id, negocio_id, conteudo_id, status, criado_em")
            .in_("negocio_id", neg_ids)
            .order("criado_em", desc=True)
            .limit(20)
            .execute()
        )
        videos = vid_result.data or []

    # Contadores por status
    conteudos_por_status = {}
    for c in conteudos:
        s = c.get("status", "?")
        conteudos_por_status[s] = conteudos_por_status.get(s, 0) + 1

    videos_por_status = {}
    for v in videos:
        s = v.get("status", "?")
        videos_por_status[s] = videos_por_status.get(s, 0) + 1

    return {
        "user": {
            "id": user_id,
            "workspace_id": workspace_id,
            "papel": current_user.get("papel"),
            "nome": current_user.get("nome"),
        },
        "negocios": negocios,
        "conteudos": conteudos,
        "videos": videos,
        "resumo": {
            "total_negocios": len(negocios),
            "total_conteudos": len(conteudos),
            "total_videos": len(videos),
            "conteudos_por_status": conteudos_por_status,
            "videos_por_status": videos_por_status,
        },
    }
