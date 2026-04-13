"""
Rotas de publicacao — dispara publicacao no YouTube e Instagram.
Sessao 12 — YouTube. Sessao 13 — Instagram (Reels via Meta Graph API).
"""

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from core.auth import get_current_user
from core.db import get_supabase
from modules.video_engine.services.publisher_youtube import publish_with_retry as youtube_publish_with_retry
from modules.video_engine.services.publisher_instagram import publish_with_retry as instagram_publish_with_retry
from modules.video_engine.services.notifier import notify_published, notify_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/publish", tags=["Publicacao"])


def _get_video_context(video_id: str, workspace_id: str) -> tuple[dict, dict, dict, dict]:
    """
    Busca video, conteudo, app e workspace.
    Valida que o video pertence ao workspace do usuario.
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

    ws_result = (
        supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
    )
    if not ws_result.data:
        raise HTTPException(status_code=404, detail="Workspace nao encontrado")
    workspace = ws_result.data[0]

    conteudo = {}
    if video.get("conteudo_id"):
        c_result = (
            supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
        )
        if c_result.data:
            conteudo = c_result.data[0]

    return video, conteudo, app, workspace


async def _publish_youtube_task(video_id: str, workspace_id: str) -> None:
    """
    Task em background que publica no YouTube com retry.
    Notifica editores sobre sucesso ou erro.
    """
    try:
        supabase = get_supabase()

        # Recarregar dados frescos
        video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
        if not video_result.data:
            logger.error(f"Video {video_id} nao encontrado para publicacao")
            return
        video = video_result.data[0]

        app_result = supabase.table("negocios").select("*").eq("id", video["negocio_id"]).execute()
        if not app_result.data:
            return
        app = app_result.data[0]

        ws_result = supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
        if not ws_result.data:
            return
        workspace = ws_result.data[0]

        conteudo = {}
        if video.get("conteudo_id"):
            c_result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
            if c_result.data:
                conteudo = c_result.data[0]

        # Marcar como publicando
        supabase.table("videos").update({
            "status": "publicando",
        }).eq("id", video_id).execute()
        video["status"] = "publicando"

        # Publicar com retry
        url = await youtube_publish_with_retry(video, conteudo, app, workspace)

        # Notificar sucesso
        # Recarregar video atualizado
        video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
        if video_result.data:
            video = video_result.data[0]

        editors_result = (
            supabase.table("users")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("ativo", True)
            .in_("papel", ["admin", "editor"])
            .execute()
        )
        editors = editors_result.data if editors_result.data else []

        notify_published(video, app, editors)

        logger.info(f"Video {video_id} publicado no YouTube: {url}")

    except Exception as e:
        logger.error(f"Erro na publicacao do video {video_id}: {e}")

        # Notificar erro
        try:
            supabase = get_supabase()
            app_result = supabase.table("negocios").select("*").eq("id", video.get("app_id", "")).execute()
            app = app_result.data[0] if app_result.data else {}

            admins_result = (
                supabase.table("users")
                .select("*")
                .eq("workspace_id", workspace_id)
                .eq("ativo", True)
                .eq("papel", "admin")
                .execute()
            )
            admins = admins_result.data if admins_result.data else []

            # Recarregar video para pegar status atualizado
            video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
            video_fresh = video_result.data[0] if video_result.data else video

            notify_error(video_fresh, app, admins, str(e))
        except Exception as notify_err:
            logger.error(f"Erro ao notificar falha de publicacao: {notify_err}")


@router.post("/youtube/{video_id}")
async def publish_youtube(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Dispara publicacao de um video no YouTube.

    Requisitos:
    - Video deve estar com status 'aprovado'
    - YouTube deve estar nas plataformas do app
    - Credenciais do YouTube devem estar configuradas

    O upload ocorre em background com ate 3 tentativas.
    """
    workspace_id = current_user["workspace_id"]
    video, conteudo, app, workspace = _get_video_context(video_id, workspace_id)

    # Validacoes
    if video["status"] not in ("aprovado",):
        raise HTTPException(
            status_code=400,
            detail=f"Video nao pode ser publicado — status atual: {video['status']}",
        )

    plataformas = app.get("plataformas") or []
    if "youtube" not in plataformas:
        raise HTTPException(
            status_code=400,
            detail="YouTube nao esta nas plataformas configuradas para este app",
        )

    # Verificar credenciais basicas
    settings_check = get_settings_check(workspace)
    if not settings_check["youtube_ok"]:
        raise HTTPException(
            status_code=400,
            detail="Credenciais do YouTube nao configuradas. "
                   "Configure YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET e YOUTUBE_REFRESH_TOKEN.",
        )

    # Disparar publicacao em background
    background_tasks.add_task(_publish_youtube_task, video_id, workspace_id)

    return {
        "status": "publicando",
        "message": "Publicacao no YouTube iniciada em background",
        "video_id": video_id,
    }


@router.post("/youtube/{video_id}/retry")
async def retry_publish_youtube(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Retenta publicacao de um video que falhou.
    Reseta o contador de tentativas e reinicia o processo.
    """
    workspace_id = current_user["workspace_id"]
    video, conteudo, app, workspace = _get_video_context(video_id, workspace_id)

    if video["status"] != "erro_publicacao":
        raise HTTPException(
            status_code=400,
            detail=f"Retry so disponivel para videos com erro_publicacao — status atual: {video['status']}",
        )

    # Resetar tentativas
    supabase = get_supabase()
    supabase.table("videos").update({
        "tentativas_publicacao": 0,
        "status": "aprovado",
        "erro_msg": None,
    }).eq("id", video_id).execute()

    # Disparar publicacao
    background_tasks.add_task(_publish_youtube_task, video_id, workspace_id)

    return {
        "status": "publicando",
        "message": "Retry de publicacao no YouTube iniciado",
        "video_id": video_id,
    }


async def _publish_instagram_task(video_id: str, workspace_id: str) -> None:
    """
    Task em background que publica no Instagram com retry.
    Notifica editores sobre sucesso ou erro.
    """
    try:
        supabase = get_supabase()

        # Recarregar dados frescos
        video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
        if not video_result.data:
            logger.error(f"Video {video_id} nao encontrado para publicacao Instagram")
            return
        video = video_result.data[0]

        app_result = supabase.table("negocios").select("*").eq("id", video["negocio_id"]).execute()
        if not app_result.data:
            return
        app = app_result.data[0]

        ws_result = supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
        if not ws_result.data:
            return
        workspace = ws_result.data[0]

        conteudo = {}
        if video.get("conteudo_id"):
            c_result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
            if c_result.data:
                conteudo = c_result.data[0]

        # Marcar como publicando
        supabase.table("videos").update({
            "status": "publicando",
        }).eq("id", video_id).execute()
        video["status"] = "publicando"

        # Publicar com retry
        url = await instagram_publish_with_retry(video, conteudo, app, workspace)

        # Notificar sucesso
        video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
        if video_result.data:
            video = video_result.data[0]

        editors_result = (
            supabase.table("users")
            .select("*")
            .eq("workspace_id", workspace_id)
            .eq("ativo", True)
            .in_("papel", ["admin", "editor"])
            .execute()
        )
        editors = editors_result.data if editors_result.data else []

        notify_published(video, app, editors)

        logger.info(f"Video {video_id} publicado no Instagram: {url}")

    except Exception as e:
        logger.error(f"Erro na publicacao Instagram do video {video_id}: {e}")

        try:
            supabase = get_supabase()
            app_result = supabase.table("negocios").select("*").eq("id", video.get("app_id", "")).execute()
            app = app_result.data[0] if app_result.data else {}

            admins_result = (
                supabase.table("users")
                .select("*")
                .eq("workspace_id", workspace_id)
                .eq("ativo", True)
                .eq("papel", "admin")
                .execute()
            )
            admins = admins_result.data if admins_result.data else []

            video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
            video_fresh = video_result.data[0] if video_result.data else video

            notify_error(video_fresh, app, admins, str(e))
        except Exception as notify_err:
            logger.error(f"Erro ao notificar falha de publicacao Instagram: {notify_err}")


@router.post("/instagram/{video_id}")
async def publish_instagram(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Dispara publicacao de um video como Reel no Instagram.

    Requisitos:
    - Video deve estar com status 'aprovado'
    - Instagram deve estar nas plataformas do app
    - Video vertical (9:16) deve existir
    - Credenciais do Instagram devem estar configuradas

    O upload ocorre em background com ate 3 tentativas.
    """
    workspace_id = current_user["workspace_id"]
    video, conteudo, app, workspace = _get_video_context(video_id, workspace_id)

    # Validacoes
    if video["status"] not in ("aprovado",):
        raise HTTPException(
            status_code=400,
            detail=f"Video nao pode ser publicado — status atual: {video['status']}",
        )

    plataformas = app.get("plataformas") or []
    if "instagram" not in plataformas:
        raise HTTPException(
            status_code=400,
            detail="Instagram nao esta nas plataformas configuradas para este app",
        )

    # Verificar video vertical
    if not video.get("url_storage_vertical"):
        raise HTTPException(
            status_code=400,
            detail="Video vertical (9:16) nao disponivel. Instagram Reels exige formato vertical.",
        )

    # Verificar credenciais
    cred_check = get_settings_check(workspace)
    if not cred_check["instagram_ok"]:
        raise HTTPException(
            status_code=400,
            detail="Credenciais do Instagram nao configuradas. "
                   "Configure META_ACCESS_TOKEN e META_INSTAGRAM_ACCOUNT_ID.",
        )

    # Disparar publicacao em background
    background_tasks.add_task(_publish_instagram_task, video_id, workspace_id)

    return {
        "status": "publicando",
        "message": "Publicacao no Instagram iniciada em background",
        "video_id": video_id,
    }


@router.post("/instagram/{video_id}/retry")
async def retry_publish_instagram(
    video_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
):
    """
    Retenta publicacao de um video no Instagram que falhou.
    Reseta o contador de tentativas e reinicia o processo.
    """
    workspace_id = current_user["workspace_id"]
    video, conteudo, app, workspace = _get_video_context(video_id, workspace_id)

    if video["status"] != "erro_publicacao":
        raise HTTPException(
            status_code=400,
            detail=f"Retry so disponivel para videos com erro_publicacao — status atual: {video['status']}",
        )

    # Resetar tentativas
    supabase = get_supabase()
    supabase.table("videos").update({
        "tentativas_publicacao": 0,
        "status": "aprovado",
        "erro_msg": None,
    }).eq("id", video_id).execute()

    # Disparar publicacao
    background_tasks.add_task(_publish_instagram_task, video_id, workspace_id)

    return {
        "status": "publicando",
        "message": "Retry de publicacao no Instagram iniciado",
        "video_id": video_id,
    }


def get_settings_check(workspace: dict) -> dict:
    """Verifica se as credenciais do YouTube e Instagram estao configuradas."""
    from core.config import get_settings
    from core.crypto import decrypt_value
    settings = get_settings()

    # YouTube (suporta campo criptografado _enc ou legado plain)
    client_id = settings.youtube_client_id
    client_secret = settings.youtube_client_secret
    ws_yt_token = workspace.get("youtube_refresh_token_enc") or workspace.get("youtube_refresh_token")
    refresh_token = decrypt_value(ws_yt_token) if ws_yt_token else settings.youtube_refresh_token

    # Instagram (suporta campo criptografado _enc ou legado plain)
    ws_meta_token = workspace.get("meta_access_token_enc") or workspace.get("meta_access_token")
    meta_token = decrypt_value(ws_meta_token) if ws_meta_token else settings.meta_access_token
    ig_account = workspace.get("meta_instagram_account_id") or settings.meta_instagram_account_id

    return {
        "youtube_ok": bool(client_id and client_secret and refresh_token),
        "instagram_ok": bool(meta_token and ig_account),
    }
