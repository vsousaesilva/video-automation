"""
Publicacao de Reels no Instagram via Meta Graph API.
Sessao 13 — upload de video vertical 9:16 como Reel.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"

# Backoff entre tentativas: 5min, 15min, 30min
RETRY_DELAYS = [300, 900, 1800]

MAX_RETRIES = 3

# Polling de processamento: 30s entre checks, max 5min (10 tentativas)
POLL_INTERVAL = 30
POLL_MAX_ATTEMPTS = 10


def _get_instagram_credentials(workspace: dict) -> tuple[str, str]:
    """
    Obtem access_token e instagram_account_id a partir do workspace.

    Prioridade:
    1. Credenciais armazenadas no workspace (meta_access_token, meta_instagram_account_id)
    2. Credenciais globais do .env (fallback)

    Returns:
        (access_token, instagram_account_id)
    """
    settings = get_settings()

    access_token = (
        workspace.get("meta_access_token")
        or settings.meta_access_token
    )
    ig_account_id = (
        workspace.get("meta_instagram_account_id")
        or settings.meta_instagram_account_id
    )

    if not access_token:
        raise ValueError(
            "Access token do Instagram nao configurado. "
            "Configure META_ACCESS_TOKEN no .env ou no workspace."
        )

    if not ig_account_id:
        raise ValueError(
            "Instagram Account ID nao configurado. "
            "Configure META_INSTAGRAM_ACCOUNT_ID no .env ou no workspace."
        )

    return access_token, ig_account_id


def _build_caption(conteudo: dict) -> str:
    """
    Monta a caption do Reel no Instagram.
    Formato: titulo + descricao_instagram + hashtags_instagram
    Limite: 2200 caracteres.
    """
    titulo = conteudo.get("titulo", "")
    descricao = conteudo.get("descricao_instagram", "")

    hashtags = conteudo.get("hashtags_instagram") or []
    hashtags_str = " ".join(
        tag if tag.startswith("#") else f"#{tag}" for tag in hashtags[:30]
    )

    caption = titulo
    if descricao:
        caption += f"\n\n{descricao}"
    if hashtags_str:
        caption += f"\n\n{hashtags_str}"

    # Instagram limita caption a 2200 caracteres
    if len(caption) > 2200:
        caption = caption[:2197] + "..."

    return caption


async def _create_signed_url(video_url: str) -> str:
    """
    Gera uma signed URL temporaria do Supabase Storage.

    A Meta Graph API precisa de uma URL publica acessivel para baixar o video.
    Se a URL ja for publica, retorna como esta.
    Se for de um bucket privado, gera signed URL com 1h de validade.
    """
    settings = get_settings()

    # Se ja eh URL publica do Supabase, converter para signed URL
    bucket_marker = "/storage/v1/object/public/"
    if bucket_marker in video_url:
        # Extrair o path relativo
        idx = video_url.find(bucket_marker)
        after_marker = video_url[idx + len(bucket_marker):]
        # Formato: bucket_name/path
        parts = after_marker.split("/", 1)
        if len(parts) == 2:
            bucket_name = parts[0]
            file_path = parts[1]

            supabase = get_supabase()
            result = supabase.storage.from_(bucket_name).create_signed_url(
                file_path, 3600  # 1 hora de validade
            )

            if result and result.get("signedURL"):
                return result["signedURL"]

    # Fallback: retorna a URL original
    return video_url


async def _create_media_container(
    ig_account_id: str,
    access_token: str,
    video_url: str,
    caption: str,
) -> str:
    """
    Passo 1: Cria o container de midia (Reel) no Instagram.
    POST /{ig-user-id}/media

    Returns:
        creation_id do container
    """
    url = f"{GRAPH_API_BASE}/{ig_account_id}/media"
    params = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, data=params)

    data = response.json()

    if "error" in data:
        error = data["error"]
        error_msg = error.get("message", str(error))
        error_code = error.get("code", "")
        error_subcode = error.get("error_subcode", "")

        # Token expirado
        if error_code == 190 or "expired" in error_msg.lower():
            raise ValueError(
                f"Token do Instagram expirado ou invalido. "
                f"Renovar o META_ACCESS_TOKEN. Erro: {error_msg}"
            )

        raise RuntimeError(
            f"Erro ao criar container Instagram: [{error_code}/{error_subcode}] {error_msg}"
        )

    creation_id = data.get("id")
    if not creation_id:
        raise RuntimeError(f"Resposta inesperada da API — sem creation_id: {data}")

    return creation_id


async def _wait_for_processing(
    creation_id: str,
    access_token: str,
) -> None:
    """
    Passo 2: Aguarda o processamento do video pelo Instagram.
    GET /{creation-id}?fields=status_code

    Faz polling a cada 30s, maximo 5 minutos.

    Status possiveis:
    - EXPIRED: falhou
    - ERROR: falhou
    - FINISHED: pronto para publicar
    - IN_PROGRESS: ainda processando
    - PUBLISHED: ja publicado
    """
    url = f"{GRAPH_API_BASE}/{creation_id}"
    params = {
        "fields": "status_code",
        "access_token": access_token,
    }

    for attempt in range(POLL_MAX_ATTEMPTS):
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)

        data = response.json()

        if "error" in data:
            error = data["error"]
            raise RuntimeError(
                f"Erro ao verificar status do container: {error.get('message', str(error))}"
            )

        status_code = data.get("status_code", "").upper()

        if status_code == "FINISHED":
            logger.info(f"Container {creation_id} processado com sucesso")
            return

        if status_code in ("ERROR", "EXPIRED"):
            raise RuntimeError(
                f"Processamento do video falhou no Instagram. Status: {status_code}"
            )

        logger.info(
            f"Container {creation_id} ainda processando (tentativa {attempt + 1}/{POLL_MAX_ATTEMPTS}). "
            f"Status: {status_code}. Aguardando {POLL_INTERVAL}s..."
        )
        await asyncio.sleep(POLL_INTERVAL)

    raise RuntimeError(
        f"Timeout aguardando processamento do Instagram apos {POLL_MAX_ATTEMPTS * POLL_INTERVAL}s"
    )


async def _publish_media(
    ig_account_id: str,
    access_token: str,
    creation_id: str,
) -> str:
    """
    Passo 3: Publica o container processado.
    POST /{ig-user-id}/media_publish

    Returns:
        media_id do post publicado
    """
    url = f"{GRAPH_API_BASE}/{ig_account_id}/media_publish"
    params = {
        "creation_id": creation_id,
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, data=params)

    data = response.json()

    if "error" in data:
        error = data["error"]
        raise RuntimeError(
            f"Erro ao publicar Reel: {error.get('message', str(error))}"
        )

    media_id = data.get("id")
    if not media_id:
        raise RuntimeError(f"Resposta inesperada da API — sem media_id: {data}")

    return media_id


async def _get_permalink(media_id: str, access_token: str) -> str:
    """
    Busca o permalink (URL publica) do Reel publicado.
    GET /{media-id}?fields=permalink
    """
    url = f"{GRAPH_API_BASE}/{media_id}"
    params = {
        "fields": "permalink",
        "access_token": access_token,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)

    data = response.json()

    permalink = data.get("permalink")
    if permalink:
        return permalink

    # Fallback: montar URL padrao
    return f"https://www.instagram.com/reel/{media_id}/"


def _log_etapa(app_id: str, video_id: str, etapa: str, status: str, mensagem: str) -> None:
    """Registra log de etapa no banco."""
    try:
        supabase = get_supabase()
        supabase.table("execution_logs").insert({
            "app_id": app_id,
            "video_id": video_id,
            "etapa": etapa,
            "status": status,
            "mensagem": mensagem,
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")


async def publish_to_instagram(
    video: dict,
    conteudo: dict,
    app: dict,
    workspace: dict,
) -> str:
    """
    Publica um video como Reel no Instagram via Meta Graph API.

    Fluxo:
    1. Gera signed URL do video vertical no Supabase Storage
    2. POST /{ig-user-id}/media — cria container com video_url + caption
    3. GET /{creation-id}?fields=status_code — aguarda processamento (poll 30s, max 5min)
    4. POST /{ig-user-id}/media_publish — publica o Reel
    5. Atualiza o banco com a URL e status

    Args:
        video: registro da tabela videos
        conteudo: registro da tabela conteudos
        app: registro da tabela apps
        workspace: registro da tabela workspaces

    Returns:
        URL do Reel publicado no Instagram

    Raises:
        ValueError: credenciais incompletas ou video indisponivel
        RuntimeError: erro da Meta Graph API
    """
    video_id = video["id"]
    app_id = app["id"]

    _log_etapa(app_id, video_id, "instagram_inicio", "info",
               "Iniciando publicacao no Instagram")

    # 1. Validar que temos video vertical
    storage_url = video.get("url_storage_vertical")
    if not storage_url:
        raise ValueError("Video vertical (9:16) nao disponivel para publicacao no Instagram")

    # 2. Obter credenciais
    access_token, ig_account_id = _get_instagram_credentials(workspace)
    _log_etapa(app_id, video_id, "instagram_auth", "info",
               "Credenciais do Instagram obtidas")

    # 3. Gerar signed URL para a Meta acessar o video
    _log_etapa(app_id, video_id, "instagram_signed_url", "info",
               "Gerando URL temporaria do video")
    signed_url = await _create_signed_url(storage_url)

    # 4. Montar caption
    caption = _build_caption(conteudo)

    # 5. Criar container de midia (Reel)
    _log_etapa(app_id, video_id, "instagram_container", "info",
               "Criando container de midia no Instagram")
    creation_id = await _create_media_container(
        ig_account_id=ig_account_id,
        access_token=access_token,
        video_url=signed_url,
        caption=caption,
    )
    _log_etapa(app_id, video_id, "instagram_container", "info",
               f"Container criado: {creation_id}")

    # 6. Aguardar processamento
    _log_etapa(app_id, video_id, "instagram_processamento", "info",
               "Aguardando processamento do video pelo Instagram")
    await _wait_for_processing(creation_id, access_token)

    # 7. Publicar o Reel
    _log_etapa(app_id, video_id, "instagram_publicar", "info",
               "Publicando Reel no Instagram")
    media_id = await _publish_media(ig_account_id, access_token, creation_id)

    # 8. Obter URL do Reel
    instagram_url = await _get_permalink(media_id, access_token)

    # 9. Atualizar banco de dados
    supabase = get_supabase()
    agora = datetime.now(timezone.utc).isoformat()

    supabase.table("videos").update({
        "url_instagram": instagram_url,
        "status": "publicado",
        "publicado_em": agora,
    }).eq("id", video_id).execute()

    # Atualizar conteudo (enum: gerado, em_producao, erro, concluido)
    if conteudo.get("id"):
        supabase.table("conteudos").update({
            "status": "concluido",
        }).eq("id", conteudo["id"]).execute()

    _log_etapa(app_id, video_id, "instagram_sucesso", "sucesso",
               f"Reel publicado com sucesso: {instagram_url}")

    return instagram_url


async def publish_with_retry(
    video: dict,
    conteudo: dict,
    app: dict,
    workspace: dict,
) -> str:
    """
    Publica no Instagram com mecanismo de retry.
    3 tentativas com backoff: 5min, 15min, 30min.

    Atualiza tentativas_publicacao no banco a cada tentativa.
    Apos 3 falhas: status = 'erro_publicacao'.

    Returns:
        URL do Reel publicado

    Raises:
        Exception: se todas as tentativas falharem
    """
    video_id = video["id"]
    app_id = app["id"]
    supabase = get_supabase()

    tentativa_atual = video.get("tentativas_publicacao", 0)
    last_error = None

    for i in range(tentativa_atual, MAX_RETRIES):
        try:
            # Atualizar contador de tentativas
            supabase.table("videos").update({
                "tentativas_publicacao": i + 1,
            }).eq("id", video_id).execute()

            _log_etapa(app_id, video_id, "instagram_tentativa", "info",
                       f"Tentativa {i + 1} de {MAX_RETRIES}")

            url = await publish_to_instagram(video, conteudo, app, workspace)
            return url

        except Exception as e:
            last_error = str(e)
            _log_etapa(app_id, video_id, "instagram_retry", "erro",
                       f"Tentativa {i + 1} falhou: {last_error}")

            # Se nao eh a ultima tentativa, aguardar backoff
            if i < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[i]
                _log_etapa(app_id, video_id, "instagram_backoff", "info",
                           f"Aguardando {delay // 60} minutos antes da proxima tentativa")
                await asyncio.sleep(delay)

                # Recarregar video do banco (pode ter sido cancelado)
                video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
                if not video_result.data:
                    raise ValueError(f"Video {video_id} nao encontrado no banco")
                video = video_result.data[0]

                # Se o status mudou (ex: cancelado manualmente), parar
                if video["status"] not in ("aprovado", "publicando"):
                    _log_etapa(app_id, video_id, "instagram_cancelado", "info",
                               f"Publicacao cancelada — status mudou para: {video['status']}")
                    raise ValueError(f"Publicacao cancelada: status={video['status']}")

    # Todas as tentativas falharam
    supabase.table("videos").update({
        "status": "erro_publicacao",
        "erro_msg": f"Falha apos {MAX_RETRIES} tentativas (Instagram): {last_error}",
    }).eq("id", video_id).execute()

    _log_etapa(app_id, video_id, "instagram_falha_final", "erro",
               f"Publicacao Instagram falhou apos {MAX_RETRIES} tentativas: {last_error}")

    raise Exception(f"Publicacao Instagram falhou apos {MAX_RETRIES} tentativas: {last_error}")
