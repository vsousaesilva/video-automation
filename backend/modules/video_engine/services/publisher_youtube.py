"""
Publicacao de videos no YouTube via Data API v3.
Sessao 12 — upload resumable com deteccao automatica de Shorts.
"""

import logging
import os
import tempfile
import time
from datetime import datetime, timezone

import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from core.config import get_settings
from core.crypto import decrypt_value
from core.db import get_supabase

logger = logging.getLogger(__name__)

# Categoria padrao: 22 = People & Blogs
DEFAULT_CATEGORY_ID = "22"

# Backoff entre tentativas: 5min, 15min, 30min
RETRY_DELAYS = [300, 900, 1800]

MAX_RETRIES = 3


def _get_youtube_credentials(workspace: dict) -> Credentials:
    """
    Monta credenciais OAuth2 para o YouTube a partir do workspace.

    Prioridade:
    1. Refresh token armazenado no workspace (youtube_refresh_token)
    2. Refresh token global do .env (fallback)
    """
    settings = get_settings()

    client_id = settings.youtube_client_id
    client_secret = settings.youtube_client_secret

    # Refresh token por workspace tem prioridade (descriptografa se armazenado criptografado)
    ws_token = workspace.get("youtube_refresh_token_enc") or workspace.get("youtube_refresh_token")
    refresh_token = decrypt_value(ws_token) if ws_token else settings.youtube_refresh_token

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Credenciais do YouTube incompletas. "
            "Configure YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET e YOUTUBE_REFRESH_TOKEN."
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
    )

    return credentials


def _build_youtube_service(credentials: Credentials):
    """Constroi o servico YouTube Data API v3."""
    return build("youtube", "v3", credentials=credentials)


def _is_short(video: dict) -> bool:
    """
    Determina se o video deve ser publicado como YouTube Short.
    Short = duracao < 60s e versao vertical disponivel.
    """
    duracao_vertical = video.get("duracao_vertical_segundos") or 0
    tem_vertical = bool(video.get("url_storage_vertical"))

    return tem_vertical and duracao_vertical > 0 and duracao_vertical < 60


def _select_video_file(video: dict, is_short: bool) -> tuple[str, int]:
    """
    Seleciona qual versao do video usar para upload.

    Retorna (url_storage, duracao_segundos).
    - Shorts: versao vertical 9:16
    - Video padrao: versao horizontal 16:9
    """
    if is_short:
        url = video.get("url_storage_vertical")
        duracao = video.get("duracao_vertical_segundos", 0)
    else:
        # Preferir horizontal; fallback para vertical se nao tiver
        url = video.get("url_storage_horizontal") or video.get("url_storage_vertical")
        duracao = video.get("duracao_horizontal_segundos") or video.get("duracao_vertical_segundos", 0)

    if not url:
        raise ValueError("Nenhuma versao de video disponivel para upload")

    return url, duracao


def _build_title(conteudo: dict, is_short: bool) -> str:
    """Monta o titulo do video, adicionando #Shorts se necessario."""
    titulo = conteudo.get("titulo", "Video")

    if is_short and "#Shorts" not in titulo:
        # YouTube exige #Shorts no titulo ou descricao para classificar como Short
        titulo = f"{titulo} #Shorts"

    # YouTube limita titulo a 100 caracteres
    if len(titulo) > 100:
        titulo = titulo[:97] + "..."

    return titulo


def _build_description(conteudo: dict, app: dict, is_short: bool) -> str:
    """Monta a descricao do video para o YouTube."""
    descricao = conteudo.get("descricao_youtube", "")

    # Adicionar CTA se disponivel
    cta = app.get("cta")
    if cta and cta not in descricao:
        descricao += f"\n\n{cta}"

    # Adicionar link de download se disponivel
    link = app.get("link_download")
    if link and link not in descricao:
        descricao += f"\n{link}"

    # Adicionar hashtags YouTube
    hashtags = conteudo.get("hashtags_youtube") or []
    if is_short and "#Shorts" not in hashtags:
        hashtags = ["#Shorts"] + hashtags

    if hashtags:
        hashtags_str = " ".join(
            tag if tag.startswith("#") else f"#{tag}" for tag in hashtags[:15]
        )
        descricao += f"\n\n{hashtags_str}"

    # YouTube limita descricao a 5000 caracteres
    if len(descricao) > 5000:
        descricao = descricao[:4997] + "..."

    return descricao


def _build_tags(conteudo: dict) -> list[str]:
    """Extrai tags a partir de hashtags e keywords SEO."""
    tags = []

    # Hashtags YouTube (sem o #)
    for h in (conteudo.get("hashtags_youtube") or []):
        tag = h.lstrip("#").strip()
        if tag:
            tags.append(tag)

    # Keywords SEO
    for k in (conteudo.get("keywords_seo") or []):
        if k.strip() and k.strip() not in tags:
            tags.append(k.strip())

    # YouTube limita a 500 caracteres no total de tags
    result = []
    total_chars = 0
    for tag in tags:
        if total_chars + len(tag) + 1 > 500:
            break
        result.append(tag)
        total_chars += len(tag) + 1  # +1 para virgula

    return result


async def _download_video_file(url: str) -> str:
    """
    Baixa o video do Supabase Storage para um arquivo temporario.
    Retorna o caminho do arquivo temporario.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.get(url)
        response.raise_for_status()

    suffix = ".mp4"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(response.content)
    tmp.close()

    return tmp.name


def _upload_to_youtube(
    youtube_service,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    category_id: str = DEFAULT_CATEGORY_ID,
) -> str:
    """
    Faz upload resumable do video para o YouTube.
    Retorna a URL do video publicado.
    """
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        file_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,  # 10MB por chunk
    )

    request = youtube_service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    # Upload resumable com progresso
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            logger.info(f"Upload YouTube: {int(status.progress() * 100)}% completo")

    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    logger.info(f"Video publicado no YouTube: {video_url}")
    return video_url


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


async def publish_to_youtube(
    video: dict,
    conteudo: dict,
    app: dict,
    workspace: dict,
) -> str:
    """
    Publica um video no YouTube usando a Data API v3.

    Fluxo:
    1. Determina se eh Short (duracao < 60s -> vertical 9:16)
    2. Baixa o arquivo do Supabase Storage
    3. Faz upload resumable para o YouTube
    4. Atualiza o banco com a URL e status

    Args:
        video: registro da tabela videos
        conteudo: registro da tabela conteudos
        app: registro da tabela apps
        workspace: registro da tabela workspaces

    Returns:
        URL do video publicado no YouTube

    Raises:
        ValueError: credenciais incompletas ou video indisponivel
        HttpError: erro da API do YouTube
    """
    video_id = video["id"]
    app_id = app["id"]

    _log_etapa(app_id, video_id, "youtube_inicio", "info",
               "Iniciando publicacao no YouTube")

    # 1. Determinar formato
    short = _is_short(video)
    formato = "Short (9:16)" if short else "Video (16:9)"
    _log_etapa(app_id, video_id, "youtube_formato", "info",
               f"Formato detectado: {formato}")

    # 2. Selecionar arquivo
    storage_url, duracao = _select_video_file(video, short)

    # 3. Montar metadados
    title = _build_title(conteudo, short)
    description = _build_description(conteudo, app, short)
    tags = _build_tags(conteudo)

    # 4. Baixar video para arquivo temporario
    _log_etapa(app_id, video_id, "youtube_download", "info",
               "Baixando video do Storage para upload")
    tmp_path = await _download_video_file(storage_url)

    try:
        # 5. Autenticar e fazer upload
        credentials = _get_youtube_credentials(workspace)
        youtube = _build_youtube_service(credentials)

        _log_etapa(app_id, video_id, "youtube_upload", "info",
                   "Iniciando upload resumable para o YouTube")

        video_url = _upload_to_youtube(
            youtube_service=youtube,
            file_path=tmp_path,
            title=title,
            description=description,
            tags=tags,
        )

        # 6. Atualizar banco de dados
        supabase = get_supabase()
        agora = datetime.now(timezone.utc).isoformat()

        supabase.table("videos").update({
            "url_youtube": video_url,
            "status": "publicado",
            "publicado_em": agora,
        }).eq("id", video_id).execute()

        # Atualizar conteudo (enum: gerado, em_producao, erro, concluido)
        if conteudo.get("id"):
            supabase.table("conteudos").update({
                "status": "concluido",
            }).eq("id", conteudo["id"]).execute()

        _log_etapa(app_id, video_id, "youtube_sucesso", "sucesso",
                   f"Video publicado com sucesso: {video_url}")

        return video_url

    except HttpError as e:
        error_reason = ""
        if e.resp and e.resp.get("status"):
            error_reason = f"HTTP {e.resp['status']}: "
        error_reason += str(e)

        # Detectar quota exceeded
        if "quotaExceeded" in str(e) or "dailyLimitExceeded" in str(e):
            _log_etapa(app_id, video_id, "youtube_quota", "erro",
                       "Cota diaria do YouTube excedida")
            raise

        # Detectar token expirado / invalido
        if "unauthorized" in str(e).lower() or "invalid_grant" in str(e).lower():
            _log_etapa(app_id, video_id, "youtube_auth", "erro",
                       "Token do YouTube expirado ou invalido")
            raise

        _log_etapa(app_id, video_id, "youtube_erro", "erro",
                   f"Erro na API do YouTube: {error_reason}")
        raise

    finally:
        # Limpar arquivo temporario
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


async def publish_with_retry(
    video: dict,
    conteudo: dict,
    app: dict,
    workspace: dict,
) -> str:
    """
    Publica no YouTube com mecanismo de retry.
    3 tentativas com backoff: 5min, 15min, 30min.

    Atualiza tentativas_publicacao no banco a cada tentativa.
    Apos 3 falhas: status = 'erro_publicacao'.

    Returns:
        URL do video publicado

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

            _log_etapa(app_id, video_id, "youtube_tentativa", "info",
                       f"Tentativa {i + 1} de {MAX_RETRIES}")

            url = await publish_to_youtube(video, conteudo, app, workspace)
            return url

        except Exception as e:
            last_error = str(e)
            _log_etapa(app_id, video_id, "youtube_retry", "erro",
                       f"Tentativa {i + 1} falhou: {last_error}")

            # Se nao eh a ultima tentativa, aguardar backoff
            if i < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[i]
                _log_etapa(app_id, video_id, "youtube_backoff", "info",
                           f"Aguardando {delay // 60} minutos antes da proxima tentativa")
                # Usar asyncio.sleep para nao bloquear
                import asyncio
                await asyncio.sleep(delay)

                # Recarregar video do banco (pode ter sido cancelado)
                video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
                if not video_result.data:
                    raise ValueError(f"Video {video_id} nao encontrado no banco")
                video = video_result.data[0]

                # Se o status mudou (ex: cancelado manualmente), parar
                if video["status"] not in ("aprovado", "publicando"):
                    _log_etapa(app_id, video_id, "youtube_cancelado", "info",
                               f"Publicacao cancelada — status mudou para: {video['status']}")
                    raise ValueError(f"Publicacao cancelada: status={video['status']}")

    # Todas as tentativas falharam
    supabase.table("videos").update({
        "status": "erro_publicacao",
        "erro_msg": f"Falha apos {MAX_RETRIES} tentativas: {last_error}",
    }).eq("id", video_id).execute()

    _log_etapa(app_id, video_id, "youtube_falha_final", "erro",
               f"Publicacao falhou apos {MAX_RETRIES} tentativas: {last_error}")

    raise Exception(f"Publicacao YouTube falhou apos {MAX_RETRIES} tentativas: {last_error}")
