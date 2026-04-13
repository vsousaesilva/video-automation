"""
Dashboard — endpoints de agregação de métricas.
GET /dashboard/overview     — KPIs gerais do workspace
GET /dashboard/video-engine — métricas detalhadas do Video Engine
GET /dashboard/usage        — consumo vs. limites do plano
GET /dashboard/timeline     — atividade recente cross-módulo
"""

from fastapi import APIRouter, Depends, Query

from core.auth import get_current_user
from modules.dashboard.services.aggregator import (
    get_overview,
    get_video_engine_metrics,
    get_usage_vs_limits,
    get_timeline,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def dashboard_overview(current_user: dict = Depends(get_current_user)):
    """KPIs gerais do workspace."""
    return get_overview(current_user["workspace_id"])


@router.get("/video-engine")
async def dashboard_video_engine(current_user: dict = Depends(get_current_user)):
    """Métricas detalhadas do Video Engine (status, evolução 30d, top negócios)."""
    return get_video_engine_metrics(current_user["workspace_id"])


@router.get("/usage")
async def dashboard_usage(current_user: dict = Depends(get_current_user)):
    """Consumo atual vs. limites do plano."""
    return get_usage_vs_limits(current_user["workspace_id"])


@router.get("/timeline")
async def dashboard_timeline(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Atividade recente cross-módulo (audit_log)."""
    return get_timeline(current_user["workspace_id"], limit=limit)
