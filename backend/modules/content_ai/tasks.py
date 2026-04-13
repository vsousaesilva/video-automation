"""
modules/content_ai/tasks.py — Tarefas Celery do módulo Content AI.
Sessão 6 — Geração em batch via fila.
"""

import asyncio
import logging

from core.tasks import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="modules.content_ai.tasks.generate_content_task",
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    acks_late=True,
)
def generate_content_task(
    self,
    workspace_id: str,
    user_id: str,
    tipo: str,
    tom_voz: str = "profissional",
    idioma: str = "pt-BR",
    negocio_id: str | None = None,
    template_id: str | None = None,
    prompt_usuario: str | None = None,
    contexto: dict | None = None,
    quantidade: int = 1,
    plataforma: str | None = None,
) -> dict:
    """Task Celery para geração de conteúdo em background."""
    logger.info(
        f"Content AI task iniciada (task_id={self.request.id}, "
        f"tipo={tipo}, quantidade={quantidade})"
    )

    try:
        from modules.content_ai.services.generator import generate_content
        result = asyncio.run(generate_content(
            workspace_id=workspace_id,
            user_id=user_id,
            tipo=tipo,
            tom_voz=tom_voz,
            idioma=idioma,
            negocio_id=negocio_id,
            template_id=template_id,
            prompt_usuario=prompt_usuario,
            contexto=contexto,
            quantidade=quantidade,
            plataforma=plataforma,
        ))

        logger.info(f"Content AI task concluída: {result['status']} ({len(result['contents'])} conteúdos)")
        return result

    except Exception as exc:
        logger.error(f"Content AI task erro (attempt {self.request.retries + 1}): {exc}")
        raise


@celery_app.task(
    bind=True,
    name="modules.content_ai.tasks.generate_batch_task",
    max_retries=1,
    acks_late=True,
)
def generate_batch_task(self, requests: list[dict]) -> dict:
    """
    Fan-out: enfileira generate_content_task para cada request do batch.
    Cada geração vira uma task individual com retry próprio.
    """
    task_ids = []
    for req in requests:
        result = generate_content_task.delay(**req)
        task_ids.append({"task_id": result.id, "tipo": req.get("tipo")})

    logger.info(f"Content AI batch: {len(requests)} gerações enfileiradas")
    return {"enqueued": len(task_ids), "tasks": task_ids}
