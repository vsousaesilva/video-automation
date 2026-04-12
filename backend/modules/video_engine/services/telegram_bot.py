"""
Serviço do Telegram Bot para aprovação de vídeos.
Sessão 11 — envio de vídeo com botões inline, notificações de publicação e erro.
"""

import json
import logging

import httpx

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}"


def _api_url(token: str) -> str:
    return TELEGRAM_API.format(token=token)


def _get_conteudo(video: dict) -> dict:
    """Busca o conteúdo associado ao vídeo."""
    if not video.get("conteudo_id"):
        return {}
    supabase = get_supabase()
    result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
    return result.data[0] if result.data else {}


def _build_approval_caption(app: dict, conteudo: dict, video: dict) -> str:
    """Monta a legenda da mensagem de aprovação."""
    titulo = conteudo.get("titulo", "(sem título)")
    tipo = conteudo.get("tipo_conteudo", "—")
    duracao = video.get("duracao_vertical_segundos") or video.get("duracao_horizontal_segundos") or 0

    return (
        f"🎬 *Novo vídeo para aprovação*\n\n"
        f"📱 *App:* {_escape_md(app['nome'])}\n"
        f"📝 *Título:* {_escape_md(titulo)}\n"
        f"🏷 *Tipo:* {_escape_md(tipo)}\n"
        f"⏱ *Duração:* {duracao}s\n\n"
        f"Escolha uma ação abaixo:"
    )


def _escape_md(text: str) -> str:
    """Escapa caracteres especiais do MarkdownV2 do Telegram."""
    special = r"_*[]()~`>#+-=|{}.!"
    result = ""
    for ch in text:
        if ch in special:
            result += f"\\{ch}"
        else:
            result += ch
    return result


def _build_inline_keyboard(video_id: str) -> dict:
    """Monta o teclado inline com os botões de ação."""
    return {
        "inline_keyboard": [
            [
                {
                    "text": "✅ Aprovar",
                    "callback_data": json.dumps({"action": "aprovar", "video_id": video_id}),
                },
                {
                    "text": "❌ Rejeitar",
                    "callback_data": json.dumps({"action": "rejeitar", "video_id": video_id}),
                },
                {
                    "text": "🔄 Regenerar",
                    "callback_data": json.dumps({"action": "regenerar", "video_id": video_id}),
                },
            ]
        ]
    }


async def send_approval_request(video: dict, app: dict, workspace: dict) -> bool:
    """
    Envia vídeo vertical para o chat do Telegram com botões inline de aprovação.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        workspace: registro da tabela workspaces

    Returns:
        True se enviou com sucesso, False caso contrário
    """
    token = workspace.get("telegram_bot_token")
    chat_id = workspace.get("telegram_chat_id")

    if not token or not chat_id:
        logger.info("Telegram não configurado no workspace — pulando envio")
        return False

    conteudo = _get_conteudo(video)
    caption = _build_approval_caption(app, conteudo, video)
    keyboard = _build_inline_keyboard(video["id"])

    video_url = video.get("url_storage_vertical")

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            if video_url:
                # Envia o vídeo com caption e botões
                response = await client.post(
                    f"{_api_url(token)}/sendVideo",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "parse_mode": "MarkdownV2",
                        "reply_markup": json.dumps(keyboard),
                    },
                    files={"video": ("video.mp4", _download_video(video_url), "video/mp4")},
                )
            else:
                # Fallback: envia apenas texto se não houver vídeo
                response = await client.post(
                    f"{_api_url(token)}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": caption,
                        "parse_mode": "MarkdownV2",
                        "reply_markup": keyboard,
                    },
                )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    message_id = result["result"]["message_id"]
                    # Salvar telegram_message_id no registro do vídeo
                    supabase = get_supabase()
                    supabase.table("videos").update({
                        "telegram_message_id": message_id,
                    }).eq("id", video["id"]).execute()
                    logger.info(
                        f"Vídeo {video['id']} enviado ao Telegram — message_id={message_id}"
                    )
                    return True
                else:
                    logger.error(f"Telegram API retornou erro: {result}")
            else:
                logger.error(
                    f"Erro HTTP {response.status_code} ao enviar para Telegram: {response.text}"
                )

    except Exception as e:
        logger.error(f"Erro ao enviar vídeo para Telegram: {e}")

    return False


def _download_video(url: str) -> bytes:
    """Baixa o vídeo do Supabase Storage para envio ao Telegram."""
    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception as e:
        logger.error(f"Erro ao baixar vídeo de {url}: {e}")
        raise


async def send_published_notification(video: dict, app: dict, workspace: dict) -> bool:
    """
    Envia notificação de vídeo publicado no Telegram.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        workspace: registro da tabela workspaces

    Returns:
        True se enviou com sucesso
    """
    token = workspace.get("telegram_bot_token")
    chat_id = workspace.get("telegram_chat_id")

    if not token or not chat_id:
        return False

    conteudo = _get_conteudo(video)
    titulo = conteudo.get("titulo", "(sem título)")

    links = ""
    if video.get("url_youtube"):
        links += f"\n🔗 YouTube: {video['url_youtube']}"
    if video.get("url_instagram"):
        links += f"\n🔗 Instagram: {video['url_instagram']}"

    text = (
        f"✅ *Vídeo publicado com sucesso\\!*\n\n"
        f"📱 *App:* {_escape_md(app['nome'])}\n"
        f"📝 *Título:* {_escape_md(titulo)}"
        f"{_escape_md(links)}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_api_url(token)}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                },
            )
            if response.status_code == 200 and response.json().get("ok"):
                logger.info(f"Notificação de publicação enviada ao Telegram — vídeo {video['id']}")
                return True
            else:
                logger.error(f"Erro ao enviar notificação de publicação: {response.text}")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de publicação ao Telegram: {e}")

    return False


async def send_error_notification(video: dict, app: dict, workspace: dict, error: str) -> bool:
    """
    Envia notificação de erro no Telegram.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        workspace: registro da tabela workspaces
        error: mensagem de erro

    Returns:
        True se enviou com sucesso
    """
    token = workspace.get("telegram_bot_token")
    chat_id = workspace.get("telegram_chat_id")

    if not token or not chat_id:
        return False

    conteudo = _get_conteudo(video)
    titulo = conteudo.get("titulo", "(sem título)")

    text = (
        f"❌ *Erro no processamento de vídeo*\n\n"
        f"📱 *App:* {_escape_md(app['nome'])}\n"
        f"📝 *Título:* {_escape_md(titulo)}\n\n"
        f"⚠️ *Erro:*\n`{_escape_md(error)}`"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_api_url(token)}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                },
            )
            if response.status_code == 200 and response.json().get("ok"):
                logger.info(f"Notificação de erro enviada ao Telegram — vídeo {video['id']}")
                return True
            else:
                logger.error(f"Erro ao enviar notificação de erro: {response.text}")
    except Exception as e:
        logger.error(f"Erro ao enviar notificação de erro ao Telegram: {e}")

    return False


async def update_telegram_message(token: str, chat_id: str, message_id: int,
                                   action: str, user_name: str) -> bool:
    """
    Atualiza a mensagem no Telegram após uma ação (remove botões e confirma).

    Args:
        token: token do bot
        chat_id: ID do chat
        message_id: ID da mensagem a editar
        action: ação realizada (aprovar/rejeitar/regenerar)
        user_name: nome do usuário que realizou a ação

    Returns:
        True se atualizou com sucesso
    """
    action_labels = {
        "aprovar": "✅ Aprovado",
        "rejeitar": "❌ Rejeitado",
        "regenerar": "🔄 Regeneração solicitada",
    }
    label = action_labels.get(action, action)
    text = f"{_escape_md(label)} por {_escape_md(user_name)}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Remove os botões inline editando o reply_markup
            await client.post(
                f"{_api_url(token)}/editMessageReplyMarkup",
                json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reply_markup": {"inline_keyboard": []},
                },
            )

            # Envia mensagem de confirmação como resposta
            response = await client.post(
                f"{_api_url(token)}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "MarkdownV2",
                    "reply_to_message_id": message_id,
                },
            )
            return response.status_code == 200

    except Exception as e:
        logger.error(f"Erro ao atualizar mensagem do Telegram: {e}")
        return False


async def register_webhook(base_url: str) -> bool:
    """
    Registra o webhook do bot no Telegram API.

    Args:
        base_url: URL base da aplicação (ex: https://sua-app.onrender.com)

    Returns:
        True se registrou com sucesso
    """
    settings = get_settings()
    token = settings.telegram_bot_token
    secret = settings.telegram_webhook_secret

    if not token:
        logger.info("TELEGRAM_BOT_TOKEN não configurado — webhook não registrado")
        return False

    webhook_url = f"{base_url}/telegram/webhook"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_api_url(token)}/setWebhook",
                json={
                    "url": webhook_url,
                    "secret_token": secret,
                    "allowed_updates": ["callback_query"],
                },
            )
            result = response.json()
            if result.get("ok"):
                logger.info(f"Webhook do Telegram registrado em {webhook_url}")
                return True
            else:
                logger.error(f"Erro ao registrar webhook: {result}")
    except Exception as e:
        logger.error(f"Erro ao registrar webhook do Telegram: {e}")

    return False
