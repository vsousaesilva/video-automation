"""
Rotas de aprovacao de videos pelo painel web.
Sessao 14 — approve, reject, regenerate com sincronizacao Telegram.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel

from core.auth import get_current_user
from core.db import get_supabase
from modules.video_engine.services.publisher_orchestrator import publish_all_platforms
from modules.video_engine.services.telegram_bot import update_telegram_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["Aprovacoes"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RejectRequest(BaseModel):
    motivo: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_video_with_context(video_id: str, workspace_id: str) -> tuple[dict, dict, dict]:
    """
    Busca video, negocio e workspace. Valida pertencimento ao workspace.
    Returns: (video, negocio, workspace)
    """
    supabase = get_supabase()

    video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        raise HTTPException(status_code=404, detail="Video nao encontrado")
    video = video_result.data[0]

    app_result = supabase.table("negocios").select("*").eq("id", video["negocio_id"]).execute()
    if not app_result.data:
        raise HTTPException(status_code=404, detail="Negócio não encontrado")
    app = app_result.data[0]

    if app["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail="Video nao encontrado")

    ws_result = supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
    if not ws_result.data:
        raise HTTPException(status_code=404, detail="Workspace nao encontrado")
    workspace = ws_result.data[0]

    return video, app, workspace


def _log_etapa(app_id: str, video_id: str, etapa: str, status: str, mensagem: str) -> None:
    """Registra log de etapa no banco."""
    try:
        supabase = get_supabase()
        supabase.table("execution_logs").insert({
            "negocio_id": app_id,
            "video_id": video_id,
            "etapa": etapa,
            "status": status,
            "mensagem": mensagem,
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")


async def _sync_telegram(workspace: dict, video: dict, action: str, user_name: str) -> None:
    """Sincroniza a acao com a mensagem do Telegram (remove botoes e confirma)."""
    token = workspace.get("telegram_bot_token")
    chat_id = workspace.get("telegram_chat_id")
    message_id = video.get("telegram_message_id")

    if not all([token, chat_id, message_id]):
        return

    await update_telegram_message(
        token=token,
        chat_id=chat_id,
        message_id=message_id,
        action=action,
        user_name=user_name,
    )


async def _publish_task(video_id: str) -> None:
    """Task em background que executa o orquestrador de publicacao."""
    try:
        await publish_all_platforms(video_id)
    except Exception as e:
        logger.error(f"Erro na publicacao orquestrada do video {video_id}: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{video_id}/approve")
async def approve_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Aprova um video pelo painel web e dispara publicacao em todas as plataformas.

    Requisitos:
    - Video deve estar com status 'aguardando_aprovacao'
    - Usuario deve ser admin ou editor do workspace

    Apos aprovacao:
    - Status -> 'aprovado'
    - Dispara orquestrador de publicacao em background
    - Sincroniza com Telegram (remove botoes da mensagem)
    """
    workspace_id = current_user["workspace_id"]
    video, app, workspace = _get_video_with_context(video_id, workspace_id)

    if video["status"] != "aguardando_aprovacao":
        raise HTTPException(
            status_code=400,
            detail=f"Video nao pode ser aprovado — status atual: {video['status']}",
        )

    if current_user["papel"] not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Apenas admins e editores podem aprovar videos")

    supabase = get_supabase()
    agora = datetime.now(timezone.utc).isoformat()

    # Atualizar status para aprovado
    supabase.table("videos").update({
        "status": "aprovado",
        "aprovado_por": current_user["id"],
        "aprovado_via": "painel",
        "aprovado_em": agora,
    }).eq("id", video_id).execute()

    # Atualizar conteudo associado (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "concluido",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(app["id"], video_id, "aprovacao_painel", "sucesso",
               f"Video aprovado via painel por {current_user['nome']}")

    # Sincronizar com Telegram
    await _sync_telegram(workspace, video, "aprovar", current_user["nome"])

    # Disparar publicacao orquestrada em background
    background_tasks.add_task(_publish_task, video_id)

    _log_etapa(app["id"], video_id, "publicacao_disparada", "info",
               "Publicacao orquestrada disparada em background apos aprovacao")

    return {
        "status": "aprovado",
        "message": f"Video aprovado por {current_user['nome']}. Publicacao iniciada em background.",
        "video_id": video_id,
    }


@router.post("/{video_id}/reject")
async def reject_video(
    video_id: str,
    body: RejectRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Rejeita um video pelo painel web com motivo obrigatorio.

    Requisitos:
    - Video deve estar com status 'aguardando_aprovacao'
    - Usuario deve ser admin ou editor do workspace

    Apos rejeicao:
    - Status -> 'rejeitado'
    - Motivo registrado no banco
    - Sincroniza com Telegram
    """
    workspace_id = current_user["workspace_id"]
    video, app, workspace = _get_video_with_context(video_id, workspace_id)

    if video["status"] != "aguardando_aprovacao":
        raise HTTPException(
            status_code=400,
            detail=f"Video nao pode ser rejeitado — status atual: {video['status']}",
        )

    if current_user["papel"] not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Apenas admins e editores podem rejeitar videos")

    supabase = get_supabase()

    supabase.table("videos").update({
        "status": "rejeitado",
        "motivo_rejeicao": body.motivo,
    }).eq("id", video_id).execute()

    # Atualizar conteudo associado (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "erro",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(app["id"], video_id, "rejeicao_painel", "sucesso",
               f"Video rejeitado via painel por {current_user['nome']}. Motivo: {body.motivo}")

    # Sincronizar com Telegram
    await _sync_telegram(workspace, video, "rejeitar", current_user["nome"])

    return {
        "status": "rejeitado",
        "message": f"Video rejeitado por {current_user['nome']}.",
        "motivo": body.motivo,
        "video_id": video_id,
    }


@router.post("/{video_id}/regenerate")
async def regenerate_video(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Descarta o video atual e reinicia o pipeline do app.

    Requisitos:
    - Video deve estar com status 'aguardando_aprovacao'
    - Usuario deve ser admin ou editor do workspace

    Apos regeneracao:
    - Video atual marcado como rejeitado (motivo: regeneracao solicitada)
    - Pipeline do app reiniciado em background
    - Sincroniza com Telegram
    """
    workspace_id = current_user["workspace_id"]
    video, app, workspace = _get_video_with_context(video_id, workspace_id)

    if video["status"] != "aguardando_aprovacao":
        raise HTTPException(
            status_code=400,
            detail=f"Video nao pode ser regenerado — status atual: {video['status']}",
        )

    if current_user["papel"] not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Apenas admins e editores podem solicitar regeneracao")

    supabase = get_supabase()

    # Marcar video atual como rejeitado
    supabase.table("videos").update({
        "status": "rejeitado",
        "motivo_rejeicao": f"Regeneracao solicitada via painel por {current_user['nome']}",
    }).eq("id", video_id).execute()

    # Marcar conteudo como erro (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "erro",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(app["id"], video_id, "regeneracao_painel", "sucesso",
               f"Regeneracao solicitada via painel por {current_user['nome']}")

    # Sincronizar com Telegram
    await _sync_telegram(workspace, video, "regenerar", current_user["nome"])

    # Reiniciar pipeline em background
    async def _regenerate_pipeline():
        try:
            from modules.video_engine.routers.pipeline import _process_negocio
            await _process_negocio(app)
        except Exception as e:
            logger.error(f"Erro ao reiniciar pipeline para app {app['nome']}: {e}")

    background_tasks.add_task(_regenerate_pipeline)

    _log_etapa(app["id"], video_id, "pipeline_reiniciado", "info",
               f"Pipeline reiniciado para app '{app['nome']}'")

    return {
        "status": "regenerando",
        "message": f"Video descartado. Novo conteudo sendo gerado para '{app['nome']}'.",
        "video_id": video_id,
    }
