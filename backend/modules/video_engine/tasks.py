"""
modules/video_engine/tasks.py — Tarefas Celery do módulo Video Engine.
Sessão 3 — Migração de asyncio.create_task / background_tasks para Celery.

Todas as tasks são síncronas (Celery workers não usam eventloop).
Funções async do pipeline são executadas via asyncio.run().
"""

import asyncio
import logging
from datetime import datetime, timezone

from core.tasks import celery_app
from core.db import get_supabase

logger = logging.getLogger(__name__)


def _log_etapa(negocio_id: str | None, etapa: str, status: str, mensagem: str) -> None:
    """Registra log de etapa no banco."""
    try:
        supabase = get_supabase()
        supabase.table("execution_logs").insert({
            "negocio_id": negocio_id,
            "etapa": etapa,
            "status": status,
            "mensagem": mensagem,
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")


@celery_app.task(
    bind=True,
    name="modules.video_engine.tasks.process_negocio_task",
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,        # Exponential backoff: 60s, 120s, 240s
    retry_backoff_max=600,     # Máximo 10 minutos entre retries
    retry_jitter=True,         # Jitter para evitar thundering herd
    acks_late=True,
)
def process_negocio_task(self, negocio: dict) -> dict:
    """
    Processa um negócio: gera conteúdo via Gemini, valida vídeo, notifica.

    Substitui: background_tasks.add_task(_process_negocio, negocio)
    """
    negocio_id = negocio.get("id", "unknown")
    negocio_nome = negocio.get("nome", "unknown")

    _log_etapa(negocio_id, "celery_task_inicio", "info",
               f"Task Celery iniciada para negócio '{negocio_nome}' "
               f"(task_id={self.request.id}, attempt={self.request.retries + 1})")

    try:
        from modules.video_engine.routers.pipeline import _process_negocio
        asyncio.run(_process_negocio(negocio))

        _log_etapa(negocio_id, "celery_task_sucesso", "sucesso",
                   f"Task Celery concluída para negócio '{negocio_nome}'")

        return {"status": "success", "negocio_id": negocio_id, "negocio_nome": negocio_nome}

    except Exception as exc:
        _log_etapa(negocio_id, "celery_task_erro", "erro",
                   f"Erro na task Celery (attempt {self.request.retries + 1}/{self.max_retries + 1}): {exc}")
        raise  # autoretry_for vai capturar e fazer retry


@celery_app.task(
    bind=True,
    name="modules.video_engine.tasks.publish_all_platforms_task",
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
)
def publish_all_platforms_task(self, video_id: str) -> dict:
    """
    Publica vídeo em todas as plataformas ativas.

    Substitui: asyncio.create_task(publish_all_platforms(video_id))
    """
    _log_etapa(None, "celery_publish_inicio", "info",
               f"Task Celery de publicação iniciada para video_id={video_id} "
               f"(task_id={self.request.id}, attempt={self.request.retries + 1})")

    try:
        from modules.video_engine.services.publisher_orchestrator import publish_all_platforms
        result = asyncio.run(publish_all_platforms(video_id))

        _log_etapa(None, "celery_publish_sucesso", "sucesso",
                   f"Publicação concluída para video_id={video_id}: {result.get('status')}")

        return {"status": result.get("status"), "video_id": video_id, "resultados": result.get("resultados")}

    except Exception as exc:
        _log_etapa(None, "celery_publish_erro", "erro",
                   f"Erro na publicação (attempt {self.request.retries + 1}/{self.max_retries + 1}): {exc}")
        raise


@celery_app.task(
    bind=True,
    name="modules.video_engine.tasks.process_all_negocios_task",
    max_retries=1,
    acks_late=True,
)
def process_all_negocios_task(self, negocios: list[dict]) -> dict:
    """
    Enfileira process_negocio_task para cada negócio.
    Fan-out: cada negócio vira uma task individual com retry próprio.
    """
    task_ids = []
    for negocio in negocios:
        result = process_negocio_task.delay(negocio)
        task_ids.append({"negocio_id": negocio["id"], "task_id": result.id})

    _log_etapa(None, "celery_fanout", "info",
               f"Fan-out: {len(negocios)} negócios enfileirados como tasks individuais")

    return {"enqueued": len(task_ids), "tasks": task_ids}
