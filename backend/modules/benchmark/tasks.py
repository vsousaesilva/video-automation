"""Tarefas Celery do Benchmark (Sessao 10)."""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="modules.benchmark.tasks.run_benchmark_analysis",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def run_benchmark_analysis(self, report_id: str):
    """Executa run_analysis em worker Celery."""
    from modules.benchmark.services.analyzer import run_analysis
    logger.info(f"[benchmark] iniciando analise report_id={report_id}")
    return run_analysis(report_id)
