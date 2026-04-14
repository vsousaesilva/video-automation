"""
core/tasks.py — Configuração do Celery app.
Sessão 3 — Fila de Processamento (Redis + Celery).
"""

import os
from celery import Celery
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "usina_do_tempo",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    # Serialização
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Retry global defaults
    task_acks_late=True,                # Ack só após conclusão (sobrevive a crash)
    worker_prefetch_multiplier=1,       # Pega 1 tarefa por vez (jobs pesados)
    task_reject_on_worker_lost=True,    # Reenfileira se worker morrer

    # Result backend
    result_expires=86400,               # Resultados expiram em 24h

    # Rotas de filas por prioridade
    task_routes={
        "modules.video_engine.tasks.process_negocio_task": {"queue": "video"},
        "modules.video_engine.tasks.publish_all_platforms_task": {"queue": "video"},
    },

    # Default queue
    task_default_queue="default",

    # Beat schedule (tarefas periódicas)
    beat_schedule={
        "rotate-execution-logs-daily": {
            "task": "core.maintenance.rotate_logs_task",
            "schedule": 86400.0,  # 24h
        },
        "sync-meta-campaigns-daily": {
            "task": "modules.ads_manager.tasks.sync_meta_campaigns_task",
            "schedule": 86400.0,  # 24h
        },
        "run-ad-rules-hourly": {
            "task": "modules.ads_manager.tasks.run_ad_rules_task",
            "schedule": 3600.0,  # 1h
        },
    },
)

# Autodiscover tasks em todos os módulos
celery_app.autodiscover_tasks([
    "modules.video_engine",
    "modules.content_ai",
    "modules.ads_manager",
    "core",
])
