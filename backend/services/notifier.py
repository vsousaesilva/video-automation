"""
Sistema de notificação por e-mail via Resend.
Sessão 10 — notificações de aprovação, publicação e erro.
"""

import logging

import resend

from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
resend.api_key = settings.resend_api_key

FROM_EMAIL = "Video Automation <noreply@resend.dev>"


# ---------------------------------------------------------------------------
# Templates HTML
# ---------------------------------------------------------------------------

def _base_template(title: str, body_html: str) -> str:
    """Template HTML base responsivo para todos os e-mails."""
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f7;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f4f7;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
  <tr>
    <td style="background-color:#1a1a2e;padding:24px 32px;">
      <h1 style="margin:0;color:#ffffff;font-size:20px;font-weight:600;">{title}</h1>
    </td>
  </tr>
  <tr>
    <td style="padding:32px;">
      {body_html}
    </td>
  </tr>
  <tr>
    <td style="background-color:#f8f9fa;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#888;font-size:12px;">Video Automation Platform</p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _approval_body(app_nome: str, tipo_conteudo: str, titulo: str,
                   duracao_vertical: int | None, duracao_horizontal: int | None,
                   approval_url: str) -> str:
    """Corpo do e-mail de solicitação de aprovação."""
    duracao_info = ""
    if duracao_vertical:
        duracao_info += f"<li><strong>Vertical (9:16):</strong> {duracao_vertical}s</li>"
    if duracao_horizontal:
        duracao_info += f"<li><strong>Horizontal (16:9):</strong> {duracao_horizontal}s</li>"

    return f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 16px;">
  Um novo vídeo foi gerado e está aguardando sua aprovação.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
  <tr>
    <td style="padding:12px 16px;background-color:#f0f4ff;border-radius:6px;">
      <p style="margin:0 0 8px;"><strong>Aplicativo:</strong> {app_nome}</p>
      <p style="margin:0 0 8px;"><strong>Título:</strong> {titulo}</p>
      <p style="margin:0 0 8px;"><strong>Tipo de conteúdo:</strong> {tipo_conteudo}</p>
      <ul style="margin:0;padding-left:20px;">{duracao_info}</ul>
    </td>
  </tr>
</table>
<table role="presentation" cellspacing="0" cellpadding="0">
  <tr>
    <td style="border-radius:6px;background-color:#1a73e8;">
      <a href="{approval_url}" target="_blank"
         style="display:inline-block;padding:14px 32px;color:#ffffff;text-decoration:none;font-size:16px;font-weight:600;">
        Revisar e Aprovar
      </a>
    </td>
  </tr>
</table>
"""


def _published_body(app_nome: str, titulo: str, url_youtube: str | None,
                    url_instagram: str | None) -> str:
    """Corpo do e-mail de vídeo publicado."""
    links = ""
    if url_youtube:
        links += f'<li><a href="{url_youtube}" style="color:#1a73e8;">YouTube</a></li>'
    if url_instagram:
        links += f'<li><a href="{url_instagram}" style="color:#1a73e8;">Instagram</a></li>'

    return f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 16px;">
  O vídeo foi publicado com sucesso!
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
  <tr>
    <td style="padding:12px 16px;background-color:#e8f5e9;border-radius:6px;">
      <p style="margin:0 0 8px;"><strong>Aplicativo:</strong> {app_nome}</p>
      <p style="margin:0 0 8px;"><strong>Título:</strong> {titulo}</p>
      <ul style="margin:0;padding-left:20px;">{links}</ul>
    </td>
  </tr>
</table>
"""


def _error_body(app_nome: str, titulo: str, error: str) -> str:
    """Corpo do e-mail de erro."""
    return f"""
<p style="color:#333;font-size:16px;line-height:1.6;margin:0 0 16px;">
  Ocorreu um erro no processamento do vídeo. É necessária intervenção manual.
</p>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
  <tr>
    <td style="padding:12px 16px;background-color:#ffeef0;border-radius:6px;">
      <p style="margin:0 0 8px;"><strong>Aplicativo:</strong> {app_nome}</p>
      <p style="margin:0 0 8px;"><strong>Título:</strong> {titulo or '(não gerado)'}</p>
      <p style="margin:0;"><strong>Erro:</strong></p>
      <pre style="background:#fff;padding:12px;border-radius:4px;font-size:13px;overflow-x:auto;color:#d32f2f;">{error}</pre>
    </td>
  </tr>
</table>
"""


# ---------------------------------------------------------------------------
# Funções de envio
# ---------------------------------------------------------------------------

def _send_email(to: list[str], subject: str, html: str) -> None:
    """Envia e-mail via Resend. Falha silenciosa com log."""
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY não configurada — e-mail não enviado")
        return

    try:
        params = {
            "from": FROM_EMAIL,
            "to": to,
            "subject": subject,
            "html": html,
        }
        resend.Emails.send(params)
        logger.info(f"E-mail enviado para {to}: {subject}")
    except Exception as e:
        logger.error(f"Erro ao enviar e-mail para {to}: {e}")


def notify_approval_needed(video: dict, app: dict, editors: list[dict]) -> None:
    """
    Notifica os editores de que um vídeo precisa de aprovação.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        editors: lista de registros da tabela users (editores + admins)
    """
    emails = [u["email"] for u in editors if u.get("email")]
    if not emails:
        logger.warning(f"Nenhum editor para notificar sobre vídeo {video['id']}")
        return

    # Buscar dados do conteúdo associado
    from db import get_supabase
    supabase = get_supabase()
    conteudo = {}
    if video.get("conteudo_id"):
        result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
        if result.data:
            conteudo = result.data[0]

    titulo = conteudo.get("titulo", "(sem título)")
    tipo_conteudo = conteudo.get("tipo_conteudo", "—")
    approval_url = f"{settings.base_url}/approvals?video_id={video['id']}"

    body = _approval_body(
        app_nome=app["nome"],
        tipo_conteudo=tipo_conteudo,
        titulo=titulo,
        duracao_vertical=video.get("duracao_vertical_segundos"),
        duracao_horizontal=video.get("duracao_horizontal_segundos"),
        approval_url=approval_url,
    )
    html = _base_template("Novo vídeo aguardando aprovação", body)
    subject = f"[Aprovação] {app['nome']} — {titulo}"

    _send_email(emails, subject, html)


def notify_published(video: dict, app: dict, editors: list[dict]) -> None:
    """
    Notifica os editores de que um vídeo foi publicado.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        editors: lista de registros da tabela users
    """
    emails = [u["email"] for u in editors if u.get("email")]
    if not emails:
        return

    from db import get_supabase
    supabase = get_supabase()
    conteudo = {}
    if video.get("conteudo_id"):
        result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
        if result.data:
            conteudo = result.data[0]

    titulo = conteudo.get("titulo", "(sem título)")

    body = _published_body(
        app_nome=app["nome"],
        titulo=titulo,
        url_youtube=video.get("url_youtube"),
        url_instagram=video.get("url_instagram"),
    )
    html = _base_template("Vídeo publicado com sucesso", body)
    subject = f"[Publicado] {app['nome']} — {titulo}"

    _send_email(emails, subject, html)


def notify_error(video: dict, app: dict, admins: list[dict], error: str) -> None:
    """
    Notifica os admins de que ocorreu um erro no vídeo.

    Args:
        video: registro da tabela videos
        app: registro da tabela apps
        admins: lista de registros da tabela users (admins)
        error: mensagem de erro
    """
    emails = [u["email"] for u in admins if u.get("email")]
    if not emails:
        return

    from db import get_supabase
    supabase = get_supabase()
    conteudo = {}
    if video.get("conteudo_id"):
        result = supabase.table("conteudos").select("*").eq("id", video["conteudo_id"]).execute()
        if result.data:
            conteudo = result.data[0]

    titulo = conteudo.get("titulo", "(sem título)")

    body = _error_body(
        app_nome=app["nome"],
        titulo=titulo,
        error=error,
    )
    html = _base_template("Erro no processamento de vídeo", body)
    subject = f"[ERRO] {app['nome']} — {titulo}"

    _send_email(emails, subject, html)