"""
routers/tasks.py — Endpoint para consultar status de tarefas Celery.
Sessão 3 — Fila de Processamento.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED
    result: dict | list | str | None = None
    error: str | None = None
    retries: int | None = None


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Consulta o status de uma tarefa Celery pelo task_id.

    Status possíveis:
    - PENDING: tarefa na fila ou ID desconhecido
    - STARTED: worker está processando
    - SUCCESS: concluída com sucesso
    - FAILURE: falhou após todas as tentativas
    - RETRY: aguardando retry
    - REVOKED: cancelada
    """
    try:
        from core.tasks import celery_app
        result = celery_app.AsyncResult(task_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Celery indisponível: {e}")

    response = TaskStatusResponse(
        task_id=task_id,
        status=result.status,
    )

    if result.successful():
        response.result = result.result
    elif result.failed():
        response.error = str(result.result)

    # Tentar obter info de retries do result info
    if result.info and isinstance(result.info, dict):
        response.retries = result.info.get("retries")

    return response


@router.post("/revoke/{task_id}")
async def revoke_task(task_id: str):
    """Cancela uma tarefa pendente ou em execução."""
    try:
        from core.tasks import celery_app
        celery_app.control.revoke(task_id, terminate=True)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Celery indisponível: {e}")

    return {"task_id": task_id, "status": "revoked"}
