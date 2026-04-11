"""
Orquestrador de publicacao em multiplas plataformas.
Sessao 14 — coordena YouTube + Instagram, purge de Storage e notificacoes.
"""

import logging
from datetime import datetime, timezone

from db import get_supabase
from services.publisher_youtube import publish_to_youtube
from services.publisher_instagram import publish_to_instagram
from services.notifier import notify_published, notify_error
from services.telegram_bot import send_published_notification, send_error_notification

logger = logging.getLogger(__name__)

VIDEOS_BUCKET = "videos"


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


def _load_context(video_id: str) -> tuple[dict, dict, dict, dict]:
    """
    Carrega video, conteudo, app e workspace a partir do video_id.

    Raises:
        ValueError: se algum registro nao for encontrado.
    """
    supabase = get_supabase()

    video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        raise ValueError(f"Video {video_id} nao encontrado")
    video = video_result.data[0]

    app_result = supabase.table("apps").select("*").eq("id", video["app_id"]).execute()
    if not app_result.data:
        raise ValueError(f"App {video['app_id']} nao encontrado")
    app = app_result.data[0]

    ws_result = supabase.table("workspaces").select("*").eq("id", app["workspace_id"]).execute()
    if not ws_result.data:
        raise ValueError(f"Workspace {app['workspace_id']} nao encontrado")
    workspace = ws_result.data[0]

    conteudo = {}
    if video.get("conteudo_id"):
        c_result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
        if c_result.data:
            conteudo = c_result.data[0]

    return video, conteudo, app, workspace


def _get_editors(workspace_id: str) -> list[dict]:
    """Busca editores e admins ativos do workspace."""
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("ativo", True)
        .in_("papel", ["admin", "editor"])
        .execute()
    )
    return result.data if result.data else []


def _extract_storage_path(url: str, bucket: str) -> str | None:
    """Extrai o path relativo do bucket a partir da URL do Supabase Storage."""
    marker = f"/storage/v1/object/public/{bucket}/"
    idx = url.find(marker)
    if idx == -1:
        return None
    return url[idx + len(marker):]


def _purge_storage(video: dict, app_id: str, video_id: str) -> None:
    """
    Remove arquivos de video temporarios do Supabase Storage.
    Mantem os registros no banco com as URLs publicas das plataformas.
    """
    supabase = get_supabase()
    paths_to_remove = []

    for url_field in ("url_storage_vertical", "url_storage_horizontal"):
        url = video.get(url_field)
        if not url:
            continue

        # Tentar extrair path do bucket "videos"
        path = _extract_storage_path(url, VIDEOS_BUCKET)
        if path:
            paths_to_remove.append(path)

        # Tambem tentar bucket "media-bank" (videos podem estar la)
        path_mb = _extract_storage_path(url, "media-bank")
        if path_mb:
            paths_to_remove.append(("media-bank", path_mb))

    if not paths_to_remove:
        _log_etapa(app_id, video_id, "purge_storage", "info",
                   "Nenhum arquivo de storage para remover")
        return

    # Remover do bucket "videos"
    videos_paths = [p for p in paths_to_remove if isinstance(p, str)]
    media_paths = [p[1] for p in paths_to_remove if isinstance(p, tuple)]

    removidos = 0
    erros = 0

    if videos_paths:
        try:
            supabase.storage.from_(VIDEOS_BUCKET).remove(videos_paths)
            removidos += len(videos_paths)
        except Exception as e:
            logger.error(f"Erro ao remover arquivos do bucket '{VIDEOS_BUCKET}': {e}")
            erros += len(videos_paths)

    if media_paths:
        try:
            supabase.storage.from_("media-bank").remove(media_paths)
            removidos += len(media_paths)
        except Exception as e:
            logger.error(f"Erro ao remover arquivos do bucket 'media-bank': {e}")
            erros += len(media_paths)

    msg = f"Purge concluido: {removidos} arquivo(s) removido(s)"
    if erros:
        msg += f", {erros} erro(s)"
    _log_etapa(app_id, video_id, "purge_storage", "sucesso" if erros == 0 else "aviso", msg)


async def publish_all_platforms(video_id: str) -> dict:
    """
    Publica o video em todas as plataformas ativas do app de forma sequencial.

    Fluxo:
    1. Carrega contexto (video, conteudo, app, workspace)
    2. Define status como 'publicando'
    3. Para cada plataforma ativa, tenta publicar
    4. Registra sucesso/falha individualmente
    5. Status final: 'publicado' (>=1 sucesso) ou 'erro_publicacao' (todas falharam)
    6. Purge do Storage se publicado com sucesso
    7. Notifica editores por e-mail + Telegram

    Args:
        video_id: ID do video a publicar

    Returns:
        dict com resultados por plataforma e status final
    """
    supabase = get_supabase()

    # 1. Carregar contexto
    video, conteudo, app, workspace = _load_context(video_id)
    app_id = app["id"]
    workspace_id = app["workspace_id"]

    _log_etapa(app_id, video_id, "orquestrador_inicio", "info",
               "Iniciando publicacao orquestrada em multiplas plataformas")

    # 2. Marcar como publicando
    supabase.table("videos").update({
        "status": "publicando",
        "tentativas_publicacao": (video.get("tentativas_publicacao") or 0) + 1,
    }).eq("id", video_id).execute()

    plataformas = app.get("plataformas") or []
    resultados = {}

    # 3. Publicar em cada plataforma ativa de forma sequencial
    if "youtube" in plataformas:
        _log_etapa(app_id, video_id, "orquestrador_youtube", "info",
                   "Publicando no YouTube...")
        try:
            url_yt = await publish_to_youtube(video, conteudo, app, workspace)
            resultados["youtube"] = {"status": "sucesso", "url": url_yt}
            _log_etapa(app_id, video_id, "orquestrador_youtube", "sucesso",
                       f"YouTube publicado: {url_yt}")
        except Exception as e:
            resultados["youtube"] = {"status": "erro", "erro": str(e)}
            _log_etapa(app_id, video_id, "orquestrador_youtube", "erro",
                       f"Falha no YouTube: {e}")

    if "instagram" in plataformas:
        _log_etapa(app_id, video_id, "orquestrador_instagram", "info",
                   "Publicando no Instagram...")
        try:
            url_ig = await publish_to_instagram(video, conteudo, app, workspace)
            resultados["instagram"] = {"status": "sucesso", "url": url_ig}
            _log_etapa(app_id, video_id, "orquestrador_instagram", "sucesso",
                       f"Instagram publicado: {url_ig}")
        except Exception as e:
            resultados["instagram"] = {"status": "erro", "erro": str(e)}
            _log_etapa(app_id, video_id, "orquestrador_instagram", "erro",
                       f"Falha no Instagram: {e}")

    # 4. Determinar status final
    sucessos = [p for p, r in resultados.items() if r["status"] == "sucesso"]
    falhas = [p for p, r in resultados.items() if r["status"] == "erro"]

    agora = datetime.now(timezone.utc).isoformat()

    if sucessos:
        status_final = "publicado"
        # Montar update com URLs das plataformas publicadas
        update_data = {
            "status": status_final,
            "publicado_em": agora,
            "erro_msg": None,
        }
        for plat, res in resultados.items():
            if res["status"] == "sucesso":
                if plat == "youtube":
                    update_data["url_youtube"] = res["url"]
                elif plat == "instagram":
                    update_data["url_instagram"] = res["url"]

        # Se houve falhas parciais, registrar no erro_msg
        if falhas:
            erros_msg = "; ".join(
                f"{p}: {resultados[p]['erro']}" for p in falhas
            )
            update_data["erro_msg"] = f"Falha parcial — {erros_msg}"

        supabase.table("videos").update(update_data).eq("id", video_id).execute()

        # Atualizar conteudo (enum: gerado, em_producao, erro, concluido)
        if conteudo.get("id"):
            supabase.table("conteudos").update({
                "status": "concluido",
            }).eq("id", conteudo["id"]).execute()

        _log_etapa(app_id, video_id, "orquestrador_status", "sucesso",
                   f"Status final: publicado. Plataformas: {', '.join(sucessos)}")

        # 5. Purge do Storage
        _log_etapa(app_id, video_id, "purge_inicio", "info",
                   "Iniciando purge de arquivos temporarios do Storage")
        _purge_storage(video, app_id, video_id)

        # 6. Notificar editores
        # Recarregar video atualizado para notificacao
        video_atualizado = supabase.table("videos").select("*").eq("id", video_id).execute()
        if video_atualizado.data:
            video_fresh = video_atualizado.data[0]
        else:
            video_fresh = video

        editors = _get_editors(workspace_id)
        notify_published(video_fresh, app, editors)
        await send_published_notification(video_fresh, app, workspace)

        _log_etapa(app_id, video_id, "orquestrador_notificacao", "sucesso",
                   "Notificacoes de publicacao enviadas (e-mail + Telegram)")

    else:
        status_final = "erro_publicacao"
        erros_msg = "; ".join(
            f"{p}: {resultados[p]['erro']}" for p in falhas
        )
        supabase.table("videos").update({
            "status": status_final,
            "erro_msg": f"Todas as plataformas falharam — {erros_msg}",
        }).eq("id", video_id).execute()

        _log_etapa(app_id, video_id, "orquestrador_status", "erro",
                   f"Status final: erro_publicacao. Falhas: {', '.join(falhas)}")

        # Notificar erro
        editors = _get_editors(workspace_id)
        admins = [u for u in editors if u["papel"] == "admin"]

        video_fresh_result = supabase.table("videos").select("*").eq("id", video_id).execute()
        video_fresh = video_fresh_result.data[0] if video_fresh_result.data else video

        notify_error(video_fresh, app, admins, erros_msg)
        await send_error_notification(video_fresh, app, workspace, erros_msg)

        _log_etapa(app_id, video_id, "orquestrador_notificacao", "sucesso",
                   "Notificacoes de erro enviadas (e-mail + Telegram)")

    _log_etapa(app_id, video_id, "orquestrador_fim", "info",
               f"Orquestracao finalizada. Status={status_final}, "
               f"Sucessos={len(sucessos)}, Falhas={len(falhas)}")

    return {
        "status": status_final,
        "resultados": resultados,
        "sucessos": sucessos,
        "falhas": falhas,
    }
