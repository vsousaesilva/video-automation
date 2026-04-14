"""
Health check detalhado e metricas basicas (Sessao 11).

`/health`           — liveness simples (sempre 200 se o processo responde)
`/health/detailed`  — valida dependencias (DB, Redis/Celery, APIs externas opcionais)
`/metrics`          — contadores agregados para monitoramento (requer token simples)
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Response, status

from core.config import get_settings
from core.observability import sentry_is_ready

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_PROCESS_STARTED_AT = time.time()


def _check_database() -> dict:
    started = time.perf_counter()
    try:
        from core.db import get_supabase
        supabase = get_supabase()
        supabase.table("plans").select("id", count="exact").limit(1).execute()
        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:  # pragma: no cover — defensivo
        return {"status": "error", "error": str(exc)[:200]}


def _check_redis() -> dict:
    settings = get_settings()
    started = time.perf_counter()
    try:
        import redis
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        return {
            "status": "ok",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)[:200]}


def _check_celery() -> dict:
    """Inspect workers ativos. 'degraded' se nao ha worker — nao derruba o app."""
    try:
        from core.tasks import celery_app
        insp = celery_app.control.inspect(timeout=1.0)
        active = insp.active() or {}
        if not active:
            return {"status": "degraded", "workers": 0}
        return {"status": "ok", "workers": len(active)}
    except Exception as exc:
        return {"status": "degraded", "error": str(exc)[:200]}


def _check_optional_apis() -> dict:
    """Apenas reporta se as chaves estao configuradas — sem fazer request."""
    settings = get_settings()
    return {
        "gemini": bool(settings.gemini_api_key),
        "asaas": bool(settings.asaas_api_key),
        "telegram": bool(settings.telegram_bot_token),
        "meta_ads": bool(settings.meta_app_id and settings.meta_app_secret),
        "google_ads": bool(settings.google_ads_developer_token),
        "tiktok_ads": bool(settings.tiktok_ads_app_id),
        "sentry": sentry_is_ready(),
    }


@router.get("/health/detailed")
async def detailed_health(response: Response) -> dict:
    settings = get_settings()
    started = time.perf_counter()

    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "celery": _check_celery(),
        "integrations": _check_optional_apis(),
    }

    # Status agregado: ok se DB ok; degraded se algum componente critico falhar
    db_ok = checks["database"]["status"] == "ok"
    aggregate = "ok" if db_ok else "error"
    if db_ok and (
        checks["redis"]["status"] != "ok" or checks["celery"]["status"] != "ok"
    ):
        aggregate = "degraded"

    if aggregate == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": aggregate,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _PROCESS_STARTED_AT, 1),
        "check_duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": checks,
    }


@router.get("/metrics")
async def metrics(x_metrics_token: str | None = Header(default=None)) -> dict:
    """Agregados simples — protegido por token quando configurado."""
    settings = get_settings()
    if settings.metrics_token and x_metrics_token != settings.metrics_token:
        raise HTTPException(status_code=401, detail="unauthorized")

    try:
        from core.db import get_supabase
        supabase = get_supabase()

        def _count(table: str, **filters) -> int:
            q = supabase.table(table).select("id", count="exact")
            for key, value in filters.items():
                q = q.eq(key, value)
            try:
                return q.execute().count or 0
            except Exception:
                return -1

        counts = {
            "workspaces": _count("workspaces"),
            "users": _count("users"),
            "negocios": _count("negocios"),
            "subscriptions_active": _count("subscriptions", status="active"),
            "videos_total": _count("videos"),
            "conteudos_total": _count("conteudos"),
            "contacts_total": _count("contacts", ativo=True),
            "benchmark_reports": _count("benchmark_reports"),
        }
    except Exception as exc:
        logger.exception("metrics_query_failed")
        counts = {"error": str(exc)[:200]}

    return {
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": round(time.time() - _PROCESS_STARTED_AT, 1),
        "sentry_enabled": sentry_is_ready(),
        "counts": counts,
    }
