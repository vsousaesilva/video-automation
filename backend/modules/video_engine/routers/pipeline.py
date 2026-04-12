import asyncio
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks

from core.db import get_supabase
from modules.video_engine.schemas import PipelineTriggerRequest, PipelineTriggerResponse
from modules.video_engine.services.gemini import generate_content, save_content, _log_etapa
from modules.video_engine.services.video_validator import (
    validate_video,
    update_video_status_error,
    update_video_status_approved,
    _log_etapa as _log_validacao,
)
from modules.video_engine.services.notifier import notify_approval_needed, notify_error
from modules.video_engine.services.telegram_bot import (
    send_approval_request as telegram_send_approval,
    send_error_notification as telegram_send_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Pipeline"])


def get_apps_for_hour(hora: int) -> list[dict]:
    """Busca apps ativos elegíveis para o horário informado."""
    supabase = get_supabase()

    result = (
        supabase.table("apps")
        .select("*")
        .eq("status", "ativo")
        .eq("horario_disparo", hora)
        .execute()
    )

    hoje = datetime.now(timezone.utc).weekday()
    dia_semana_hoje = (hoje + 1) % 7  # Converter: Python seg=0 -> nosso 1, dom=6 -> nosso 0

    apps_elegiveis = []
    for app in result.data:
        # Verificar frequência e dias da semana
        if app.get("frequencia") != "diaria" and app.get("dias_semana"):
            if dia_semana_hoje not in app["dias_semana"]:
                continue
        apps_elegiveis.append(app)

    return apps_elegiveis


def _get_last_7_types(app_id: str) -> list[str]:
    """Busca os últimos 7 tipos de conteúdo gerados para o app."""
    supabase = get_supabase()
    result = (
        supabase.table("conteudos")
        .select("tipo_conteudo")
        .eq("app_id", app_id)
        .order("criado_em", desc=True)
        .limit(7)
        .execute()
    )
    return [r["tipo_conteudo"] for r in result.data if r.get("tipo_conteudo")]


def _check_duplicate(app_id: str) -> bool:
    """Verifica se já existe conteúdo gerado hoje para o app (idempotência)."""
    supabase = get_supabase()
    hoje = datetime.now(timezone.utc).date().isoformat()

    result = (
        supabase.table("conteudos")
        .select("id")
        .eq("app_id", app_id)
        .neq("status", "erro")
        .gte("criado_em", f"{hoje}T00:00:00+00:00")
        .lte("criado_em", f"{hoje}T23:59:59+00:00")
        .execute()
    )
    return len(result.data) > 0


async def _process_app(app: dict):
    """Processa um app: gera conteúdo via Gemini e salva no banco."""
    app_id = app["id"]
    app_nome = app["nome"]

    try:
        _log_etapa(app_id, "pipeline_inicio", "info",
                   f"Iniciando pipeline para app '{app_nome}'")

        # Verificar idempotência
        if _check_duplicate(app_id):
            _log_etapa(app_id, "pipeline_duplicado", "info",
                       f"Conteúdo já gerado hoje para '{app_nome}'. Pulando.")
            return

        # Buscar workspace do app
        supabase = get_supabase()
        ws_result = (
            supabase.table("workspaces")
            .select("*")
            .eq("id", app["workspace_id"])
            .execute()
        )
        if not ws_result.data:
            _log_etapa(app_id, "pipeline_erro", "erro",
                       f"Workspace {app['workspace_id']} não encontrado")
            return

        workspace = ws_result.data[0]

        # Buscar últimos 7 tipos
        last_7_types = _get_last_7_types(app_id)

        # Gerar conteúdo via Gemini
        conteudo = await generate_content(app, workspace, last_7_types)

        # Salvar no banco
        saved = await save_content(app_id, conteudo)

        _log_etapa(app_id, "pipeline_concluido", "sucesso",
                   f"Pipeline concluído para '{app_nome}'. Conteúdo id={saved['id']}")

        # --- Sessão 10: Validação + Notificação ---
        # Buscar vídeo gerado associado ao conteúdo (se existir)
        video_result = (
            supabase.table("videos")
            .select("*")
            .eq("conteudo_id", saved["id"])
            .execute()
        )

        if video_result.data:
            video = video_result.data[0]
            video_id = video["id"]

            _log_validacao(app_id, video_id, "validacao_inicio", "info",
                           f"Iniciando validação do vídeo {video_id}")

            validation = validate_video(video, app)

            # Buscar editores e admins do workspace para notificação
            editors_result = (
                supabase.table("users")
                .select("*")
                .eq("workspace_id", app["workspace_id"])
                .eq("ativo", True)
                .in_("papel", ["admin", "editor"])
                .execute()
            )
            editors = editors_result.data if editors_result.data else []

            if validation.is_valid:
                update_video_status_approved(video_id)
                _log_validacao(app_id, video_id, "validacao_sucesso", "sucesso",
                               "Vídeo validado com sucesso")
                notify_approval_needed(video, app, editors)
                _log_validacao(app_id, video_id, "notificacao_aprovacao", "sucesso",
                               "E-mail de aprovação enviado aos editores")

                # Enviar para Telegram (se configurado)
                telegram_ok = await telegram_send_approval(video, app, workspace)
                if telegram_ok:
                    _log_validacao(app_id, video_id, "telegram_aprovacao", "sucesso",
                                   "Vídeo enviado ao Telegram para aprovação")
            else:
                update_video_status_error(video_id, validation.errors)
                erro_str = "; ".join(validation.errors)
                _log_validacao(app_id, video_id, "validacao_erro", "erro",
                               f"Validação falhou: {erro_str}")
                # Notificar admins sobre o erro
                admins = [u for u in editors if u["papel"] == "admin"]
                notify_error(video, app, admins, erro_str)
                _log_validacao(app_id, video_id, "notificacao_erro", "sucesso",
                               "E-mail de erro enviado aos admins")

                # Notificar erro via Telegram (se configurado)
                await telegram_send_error(video, app, workspace, erro_str)

    except Exception as e:
        logger.error(f"Erro no pipeline do app {app_nome}: {e}")
        _log_etapa(app_id, "pipeline_erro", "erro",
                   f"Erro no pipeline: {str(e)}")

        # Salvar conteúdo com status erro se possível
        try:
            supabase = get_supabase()
            supabase.table("conteudos").insert({
                "app_id": app_id,
                "status": "erro",
                "erro_msg": str(e),
                "criado_em": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass


async def _process_all_apps(apps: list[dict]):
    """Processa todos os apps elegíveis de forma assíncrona."""
    tasks = [_process_app(app) for app in apps]
    await asyncio.gather(*tasks, return_exceptions=True)


@router.post("/trigger", response_model=PipelineTriggerResponse)
async def trigger_pipeline(
    body: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint que recebe webhook do pg_cron.
    Valida hora, busca apps elegíveis, inicia processamento em background.
    Retorna imediatamente 200.
    """
    hora = body.hora_atual

    _log_etapa(
        app_id=None,
        etapa="trigger_recebido",
        status="info",
        mensagem=f"Trigger recebido para hora={hora}",
    )

    apps = get_apps_for_hour(hora)
    nomes = [a["nome"] for a in apps]

    if not apps:
        _log_etapa(
            app_id=None,
            etapa="trigger_vazio",
            status="info",
            mensagem=f"Nenhum app elegível para hora={hora}",
        )
        return PipelineTriggerResponse(status="no_apps", apps_triggered=[])

    _log_etapa(
        app_id=None,
        etapa="trigger_apps",
        status="info",
        mensagem=f"Apps elegíveis para hora={hora}: {', '.join(nomes)}",
    )

    background_tasks.add_task(_process_all_apps, apps)

    return PipelineTriggerResponse(status="processing", apps_triggered=nomes)
