"""
Rotas de vídeos — listagem de pendentes, detalhes e retry de publicacao.
Sessao 10 — endpoints de consulta para o painel de aprovacao.
Sessao 14 — retry manual de publicacao com falha.
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from core.auth import get_current_user
from core.db import get_supabase
from modules.video_engine.schemas import VideoResponse, VideoDetailResponse, ConteudoResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["Vídeos"])


@router.get("/pending", response_model=list[VideoResponse])
async def list_pending_videos(
    app_id: Optional[str] = Query(None, description="Filtrar por app"),
    current_user: dict = Depends(get_current_user),
):
    """Lista vídeos aguardando aprovação do workspace do usuário."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Buscar apps do workspace para filtrar vídeos
    query = (
        supabase.table("videos")
        .select("*, apps!inner(workspace_id)")
        .eq("status", "aguardando_aprovacao")
        .eq("apps.workspace_id", workspace_id)
        .order("criado_em", desc=True)
    )

    if app_id:
        query = query.eq("app_id", app_id)

    result = query.execute()

    # Remover dados do join aninhado antes de retornar
    videos = []
    for row in result.data:
        row.pop("apps", None)
        videos.append(row)

    return videos


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video_detail(
    video_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retorna detalhes completos de um vídeo, incluindo conteúdo associado."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Buscar vídeo
    video_result = (
        supabase.table("videos")
        .select("*")
        .eq("id", video_id)
        .execute()
    )

    if not video_result.data:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    video = video_result.data[0]

    # Verificar se o vídeo pertence ao workspace do usuário
    app_result = (
        supabase.table("apps")
        .select("nome, workspace_id")
        .eq("id", video["app_id"])
        .execute()
    )

    if not app_result.data or app_result.data[0]["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Vídeo não encontrado")

    app_data = app_result.data[0]

    # Buscar conteúdo associado
    conteudo = None
    if video.get("conteudo_id"):
        conteudo_result = (
            supabase.table("conteudos")
            .select("*")
            .eq("id", video["conteudo_id"])
            .execute()
        )
        if conteudo_result.data:
            conteudo = ConteudoResponse(**conteudo_result.data[0])

    return VideoDetailResponse(
        **video,
        app_nome=app_data["nome"],
        conteudo=conteudo,
    )


@router.post("/{video_id}/retry-publish")
async def retry_publish(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Retry manual de publicacao para videos com erro.

    Requisitos:
    - Video deve estar com status 'erro_publicacao'
    - Usuario deve ser admin ou editor do workspace

    Reseta o contador de tentativas e dispara o orquestrador de publicacao.
    """
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Buscar video
    video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        raise HTTPException(status_code=404, detail="Video nao encontrado")
    video = video_result.data[0]

    # Verificar pertencimento ao workspace
    app_result = supabase.table("apps").select("workspace_id").eq("id", video["app_id"]).execute()
    if not app_result.data or app_result.data[0]["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Video nao encontrado")

    # Validar status
    if video["status"] != "erro_publicacao":
        raise HTTPException(
            status_code=400,
            detail=f"Retry disponivel apenas para videos com erro_publicacao — status atual: {video['status']}",
        )

    if current_user["papel"] not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Apenas admins e editores podem solicitar retry")

    # Resetar tentativas e status
    supabase.table("videos").update({
        "tentativas_publicacao": 0,
        "status": "aprovado",
        "erro_msg": None,
    }).eq("id", video_id).execute()

    # Log
    try:
        supabase.table("execution_logs").insert({
            "app_id": video["app_id"],
            "video_id": video_id,
            "etapa": "retry_publicacao",
            "status": "info",
            "mensagem": f"Retry de publicacao solicitado por {current_user['nome']}",
        }).execute()
    except Exception:
        pass

    # Disparar orquestrador em background
    async def _retry_task():
        try:
            from modules.video_engine.services.publisher_orchestrator import publish_all_platforms
            await publish_all_platforms(video_id)
        except Exception as e:
            logger.error(f"Erro no retry de publicacao do video {video_id}: {e}")

    background_tasks.add_task(_retry_task)

    return {
        "status": "publicando",
        "message": "Retry de publicacao iniciado em background",
        "video_id": video_id,
    }
