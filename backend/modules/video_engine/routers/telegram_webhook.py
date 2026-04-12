"""
Webhook do Telegram Bot para processar callback queries de aprovação.
Sessão 11 — recebe ações dos botões inline e sincroniza com o banco.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
import httpx

from core.config import get_settings
from core.db import get_supabase
from modules.video_engine.services.telegram_bot import update_telegram_message, TELEGRAM_API

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["Telegram"])

settings = get_settings()


def _validate_secret_token(request: Request) -> None:
    """Valida o secret_token enviado pelo Telegram no header."""
    expected = settings.telegram_webhook_secret
    if not expected:
        return  # Se não configurado, aceita qualquer requisição (dev)

    received = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if received != expected:
        raise HTTPException(status_code=403, detail="Secret token inválido")


def _find_user_by_telegram_id(telegram_user_id: int) -> dict | None:
    """Busca usuário no banco pelo telegram_user_id."""
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("telegram_user_id", telegram_user_id)
        .eq("ativo", True)
        .in_("papel", ["admin", "editor"])
        .execute()
    )
    return result.data[0] if result.data else None


def _get_video_with_app(video_id: str) -> tuple[dict | None, dict | None, dict | None]:
    """Busca vídeo, app e workspace associados."""
    supabase = get_supabase()

    video_result = supabase.table("videos").select("*").eq("id", video_id).execute()
    if not video_result.data:
        return None, None, None
    video = video_result.data[0]

    app_result = supabase.table("apps").select("*").eq("id", video["app_id"]).execute()
    if not app_result.data:
        return video, None, None
    app = app_result.data[0]

    ws_result = supabase.table("workspaces").select("*").eq("id", app["workspace_id"]).execute()
    workspace = ws_result.data[0] if ws_result.data else None

    return video, app, workspace


def _log_etapa(app_id: str | None, video_id: str | None, etapa: str,
               status: str, mensagem: str) -> None:
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


async def _handle_aprovar(video: dict, user: dict, app: dict = None, workspace: dict = None) -> dict:
    """Processa aprovação do vídeo e dispara publicação orquestrada em todas as plataformas."""
    supabase = get_supabase()
    agora = datetime.now(timezone.utc).isoformat()

    supabase.table("videos").update({
        "status": "aprovado",
        "aprovado_por": user["id"],
        "aprovado_via": "telegram",
        "aprovado_em": agora,
    }).eq("id", video["id"]).execute()

    # Atualizar status do conteúdo associado (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "concluido",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(video["app_id"], video["id"], "aprovacao_telegram", "sucesso",
               f"Vídeo aprovado via Telegram por {user['nome']}")

    # Disparar publicação orquestrada em todas as plataformas ativas
    if app and workspace:
        try:
            from modules.video_engine.services.publisher_orchestrator import publish_all_platforms
            import asyncio
            asyncio.create_task(publish_all_platforms(video["id"]))
            _log_etapa(video["app_id"], video["id"], "orquestrador_auto_trigger", "info",
                       "Publicação orquestrada disparada automaticamente após aprovação via Telegram")
        except Exception as e:
            logger.error(f"Erro ao disparar publicação orquestrada: {e}")

    return {"status": "aprovado", "message": f"Vídeo aprovado por {user['nome']}"}


async def _handle_rejeitar(video: dict, user: dict) -> dict:
    """Processa rejeição do vídeo."""
    supabase = get_supabase()

    supabase.table("videos").update({
        "status": "rejeitado_telegram",
        "motivo_rejeicao": f"Rejeitado via Telegram por {user['nome']}",
    }).eq("id", video["id"]).execute()

    # Atualizar status do conteúdo associado (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "erro",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(video["app_id"], video["id"], "rejeicao_telegram", "sucesso",
               f"Vídeo rejeitado via Telegram por {user['nome']}")

    return {"status": "rejeitado_telegram", "message": f"Vídeo rejeitado por {user['nome']}"}


async def _handle_regenerar(video: dict, app: dict, user: dict) -> dict:
    """Processa solicitação de regeneração — reinicia o pipeline para o app."""
    supabase = get_supabase()

    # Marcar vídeo atual como rejeitado
    supabase.table("videos").update({
        "status": "rejeitado_telegram",
        "motivo_rejeicao": f"Regeneração solicitada via Telegram por {user['nome']}",
    }).eq("id", video["id"]).execute()

    # Marcar conteúdo como erro (enum: gerado, em_producao, erro, concluido)
    if video.get("conteudo_id"):
        supabase.table("conteudos").update({
            "status": "erro",
        }).eq("id", video["conteudo_id"]).execute()

    _log_etapa(video["app_id"], video["id"], "regeneracao_telegram", "sucesso",
               f"Regeneração solicitada via Telegram por {user['nome']}")

    # Disparar novo pipeline em background
    try:
        from modules.video_engine.routers.pipeline import _process_app
        import asyncio
        asyncio.create_task(_process_app(app))
        logger.info(f"Pipeline reiniciado para app {app['nome']} por solicitação Telegram")
    except Exception as e:
        logger.error(f"Erro ao reiniciar pipeline: {e}")

    return {"status": "regenerando", "message": f"Regeneração solicitada por {user['nome']}"}


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Endpoint que recebe callback queries do Telegram Bot.

    O Telegram envia um Update com callback_query quando o usuário
    clica em um botão inline.
    """
    _validate_secret_token(request)

    body = await request.json()
    logger.debug(f"Telegram webhook recebido: {json.dumps(body, indent=2)}")

    # Processar apenas callback_query (cliques em botões inline)
    callback_query = body.get("callback_query")
    if not callback_query:
        return {"ok": True}

    callback_id = callback_query["id"]
    telegram_user = callback_query["from"]
    telegram_user_id = telegram_user["id"]
    data_str = callback_query.get("data", "")

    # Parsear callback_data
    try:
        data = json.loads(data_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"callback_data inválido: {data_str}")
        await _answer_callback(callback_id, "Dados inválidos")
        return {"ok": True}

    action = data.get("action")
    video_id = data.get("video_id")

    if not action or not video_id:
        await _answer_callback(callback_id, "Dados incompletos")
        return {"ok": True}

    # Validar que o telegram_user_id pertence a um Admin ou Editor
    user = _find_user_by_telegram_id(telegram_user_id)
    if not user:
        await _answer_callback(
            callback_id,
            "Usuário não autorizado. Vincule seu Telegram nas configurações."
        )
        return {"ok": True}

    # Buscar vídeo, app e workspace
    video, app, workspace = _get_video_with_app(video_id)
    if not video:
        await _answer_callback(callback_id, "Vídeo não encontrado")
        return {"ok": True}

    # Verificar que o usuário pertence ao mesmo workspace do app
    if user["workspace_id"] != app.get("workspace_id"):
        await _answer_callback(callback_id, "Sem permissão para este vídeo")
        return {"ok": True}

    # Verificar se o vídeo ainda está aguardando aprovação
    if video["status"] != "aguardando_aprovacao":
        await _answer_callback(
            callback_id,
            f"Este vídeo já foi processado (status: {video['status']})"
        )
        return {"ok": True}

    # Processar a ação
    handlers = {
        "aprovar": lambda: _handle_aprovar(video, user, app, workspace),
        "rejeitar": lambda: _handle_rejeitar(video, user),
        "regenerar": lambda: _handle_regenerar(video, app, user),
    }

    handler = handlers.get(action)
    if not handler:
        await _answer_callback(callback_id, f"Ação desconhecida: {action}")
        return {"ok": True}

    result = await handler()

    # Atualizar mensagem no Telegram (remover botões, confirmar ação)
    if workspace:
        token = workspace.get("telegram_bot_token", "")
        chat_id = workspace.get("telegram_chat_id", "")
        message_id = video.get("telegram_message_id")
        if token and chat_id and message_id:
            await update_telegram_message(
                token=token,
                chat_id=chat_id,
                message_id=message_id,
                action=action,
                user_name=user["nome"],
            )

    # Responder ao callback do Telegram
    await _answer_callback(callback_id, result["message"])

    return {"ok": True}


async def _answer_callback(callback_query_id: str, text: str) -> None:
    """Responde ao callback query do Telegram (toast no app do usuário)."""
    token = settings.telegram_bot_token
    if not token:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{TELEGRAM_API.format(token=token)}/answerCallbackQuery",
                json={
                    "callback_query_id": callback_query_id,
                    "text": text,
                    "show_alert": True,
                },
            )
    except Exception as e:
        logger.error(f"Erro ao responder callback: {e}")
