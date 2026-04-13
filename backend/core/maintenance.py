"""
Tarefas de manutenção: rotação de logs, limpeza de dados agendados para exclusão.
"""

import logging
from datetime import datetime, timezone

from core.tasks import celery_app
from core.db import get_supabase

logger = logging.getLogger(__name__)


@celery_app.task(name="core.maintenance.rotate_logs_task", bind=True)
def rotate_logs_task(self):
    """Remove execution_logs com mais de 90 dias e audit_logs com mais de 365 dias."""
    supabase = get_supabase()

    # Rotação de execution_logs (90 dias)
    try:
        result = supabase.rpc("rotate_execution_logs", {"dias": 90}).execute()
        deleted = result.data if result.data else 0
        logger.info(f"Rotação de execution_logs: {deleted} registros removidos")
    except Exception as e:
        logger.warning(f"Erro na rotação de execution_logs: {e}")

    # Rotação de audit_logs (365 dias)
    try:
        result = supabase.rpc("rotate_audit_logs", {"dias": 365}).execute()
        deleted = result.data if result.data else 0
        logger.info(f"Rotação de audit_logs: {deleted} registros removidos")
    except Exception as e:
        logger.warning(f"Erro na rotação de audit_logs: {e}")

    # Processamento de exclusões LGPD agendadas
    try:
        _process_scheduled_deletions()
    except Exception as e:
        logger.error(f"Erro ao processar exclusões LGPD: {e}")


def _process_scheduled_deletions():
    """Exclui workspaces cujo prazo de carência (30 dias) já passou."""
    supabase = get_supabase()
    now = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("workspaces")
        .select("id, nome")
        .not_.is_("deletion_scheduled_for", "null")
        .lte("deletion_scheduled_for", now)
        .execute()
    )

    for ws in result.data or []:
        workspace_id = ws["id"]
        logger.info(f"Processando exclusão LGPD do workspace {workspace_id} ({ws['nome']})")

        # Desativar todos os users
        supabase.table("users").update({"ativo": False}).eq("workspace_id", workspace_id).execute()

        # Anonimizar dados pessoais
        supabase.table("users").update({
            "nome": "Usuário removido",
            "email": f"removed-{workspace_id[:8]}@deleted.local",
            "senha_hash": "",
            "reset_token": None,
        }).eq("workspace_id", workspace_id).execute()

        supabase.table("workspaces").update({
            "nome": f"Workspace removido ({workspace_id[:8]})",
            "email_cobranca": None,
            "documento_titular": None,
            "telefone": None,
        }).eq("id", workspace_id).execute()

        logger.info(f"Workspace {workspace_id} anonimizado com sucesso (LGPD)")
