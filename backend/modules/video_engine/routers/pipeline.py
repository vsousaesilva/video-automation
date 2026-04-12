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


def get_negocios_for_hour(hora: int) -> list[dict]:
    """Busca negócios ativos elegíveis para o horário informado."""
    supabase = get_supabase()

    result = (
        supabase.table("negocios")
        .select("*")
        .eq("status", "ativo")
        .eq("horario_disparo", hora)
        .execute()
    )

    hoje = datetime.now(timezone.utc).weekday()
    dia_semana_hoje = (hoje + 1) % 7  # Converter: Python seg=0 -> nosso 1, dom=6 -> nosso 0

    negocios_elegiveis = []
    for app in result.data:
        # Verificar frequência e dias da semana
        if app.get("frequencia") != "diaria" and app.get("dias_semana"):
            if dia_semana_hoje not in app["dias_semana"]:
                continue
        negocios_elegiveis.append(app)

    return negocios_elegiveis


def _get_last_7_types(negocio_id: str) -> list[str]:
    """Busca os últimos 7 tipos de conteúdo gerados para o negócio."""
    supabase = get_supabase()
    result = (
        supabase.table("conteudos")
        .select("tipo_conteudo")
        .eq("negocio_id", negocio_id)
        .order("criado_em", desc=True)
        .limit(7)
        .execute()
    )
    return [r["tipo_conteudo"] for r in result.data if r.get("tipo_conteudo")]


def _check_duplicate(negocio_id: str) -> bool:
    """Verifica se já existe conteúdo gerado hoje para o negócio (idempotência)."""
    supabase = get_supabase()
    hoje = datetime.now(timezone.utc).date().isoformat()

    result = (
        supabase.table("conteudos")
        .select("id")
        .eq("negocio_id", negocio_id)
        .neq("status", "erro")
        .gte("criado_em", f"{hoje}T00:00:00+00:00")
        .lte("criado_em", f"{hoje}T23:59:59+00:00")
        .execute()
    )
    return len(result.data) > 0


async def _process_negocio(negocio: dict):
    """Processa um negócio: gera conteúdo via Gemini e salva no banco."""
    negocio_id = negocio["id"]
    negocio_nome = negocio["nome"]

    try:
        _log_etapa(negocio_id, "pipeline_inicio", "info",
                   f"Iniciando pipeline para negócio '{negocio_nome}'")

        # Verificar idempotência
        if _check_duplicate(negocio_id):
            _log_etapa(negocio_id, "pipeline_duplicado", "info",
                       f"Conteúdo já gerado hoje para '{negocio_nome}'. Pulando.")
            return

        # Buscar workspace do negócio
        supabase = get_supabase()
        ws_result = (
            supabase.table("workspaces")
            .select("*")
            .eq("id", negocio["workspace_id"])
            .execute()
        )
        if not ws_result.data:
            _log_etapa(negocio_id, "pipeline_erro", "erro",
                       f"Workspace {negocio['workspace_id']} não encontrado")
            return

        workspace = ws_result.data[0]

        # Buscar últimos 7 tipos
        last_7_types = _get_last_7_types(negocio_id)

        # Gerar conteúdo via Gemini
        conteudo = await generate_content(negocio, workspace, last_7_types)

        # Salvar no banco
        saved = await save_content(negocio_id, conteudo)

        _log_etapa(negocio_id, "pipeline_concluido", "sucesso",
                   f"Pipeline concluído para '{negocio_nome}'. Conteúdo id={saved['id']}")

        # --- Validação + Notificação ---
        video_result = (
            supabase.table("videos")
            .select("*")
            .eq("conteudo_id", saved["id"])
            .execute()
        )

        if video_result.data:
            video = video_result.data[0]
            video_id = video["id"]

            _log_validacao(negocio_id, video_id, "validacao_inicio", "info",
                           f"Iniciando validação do vídeo {video_id}")

            validation = validate_video(video, negocio)

            editors_result = (
                supabase.table("users")
                .select("*")
                .eq("workspace_id", negocio["workspace_id"])
                .eq("ativo", True)
                .in_("papel", ["admin", "editor"])
                .execute()
            )
            editors = editors_result.data if editors_result.data else []

            if validation.is_valid:
                update_video_status_approved(video_id)
                _log_validacao(negocio_id, video_id, "validacao_sucesso", "sucesso",
                               "Vídeo validado com sucesso")
                notify_approval_needed(video, negocio, editors)
                _log_validacao(negocio_id, video_id, "notificacao_aprovacao", "sucesso",
                               "E-mail de aprovação enviado aos editores")

                telegram_ok = await telegram_send_approval(video, negocio, workspace)
                if telegram_ok:
                    _log_validacao(negocio_id, video_id, "telegram_aprovacao", "sucesso",
                                   "Vídeo enviado ao Telegram para aprovação")
            else:
                update_video_status_error(video_id, validation.errors)
                erro_str = "; ".join(validation.errors)
                _log_validacao(negocio_id, video_id, "validacao_erro", "erro",
                               f"Validação falhou: {erro_str}")
                admins = [u for u in editors if u["papel"] == "admin"]
                notify_error(video, negocio, admins, erro_str)
                _log_validacao(negocio_id, video_id, "notificacao_erro", "sucesso",
                               "E-mail de erro enviado aos admins")

                await telegram_send_error(video, negocio, workspace, erro_str)

    except Exception as e:
        logger.error(f"Erro no pipeline do negócio {negocio_nome}: {e}")
        _log_etapa(negocio_id, "pipeline_erro", "erro",
                   f"Erro no pipeline: {str(e)}")

        try:
            supabase = get_supabase()
            supabase.table("conteudos").insert({
                "negocio_id": negocio_id,
                "status": "erro",
                "erro_msg": str(e),
                "criado_em": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass


async def _process_all_negocios(negocios: list[dict]):
    """Processa todos os negócios elegíveis de forma assíncrona."""
    tasks = [_process_negocio(neg) for neg in negocios]
    await asyncio.gather(*tasks, return_exceptions=True)


@router.post("/trigger", response_model=PipelineTriggerResponse)
async def trigger_pipeline(
    body: PipelineTriggerRequest,
    background_tasks: BackgroundTasks,
):
    """
    Endpoint que recebe webhook do pg_cron.
    Valida hora, busca negócios elegíveis, inicia processamento em background.
    """
    hora = body.hora_atual

    _log_etapa(
        app_id=None,
        etapa="trigger_recebido",
        status="info",
        mensagem=f"Trigger recebido para hora={hora}",
    )

    negocios = get_negocios_for_hour(hora)
    nomes = [n["nome"] for n in negocios]

    if not negocios:
        _log_etapa(
            app_id=None,
            etapa="trigger_vazio",
            status="info",
            mensagem=f"Nenhum negócio elegível para hora={hora}",
        )
        return PipelineTriggerResponse(status="no_negocios", negocios_triggered=[])

    _log_etapa(
        app_id=None,
        etapa="trigger_negocios",
        status="info",
        mensagem=f"Negócios elegíveis para hora={hora}: {', '.join(nomes)}",
    )

    background_tasks.add_task(_process_all_negocios, negocios)

    return PipelineTriggerResponse(status="processing", negocios_triggered=nomes)
