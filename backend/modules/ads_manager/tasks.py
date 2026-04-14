"""
Tarefas Celery do Ads Manager.
Sessao 8 — Meta Ads.
"""

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="modules.ads_manager.tasks.sync_meta_campaigns_task", bind=True)
def sync_meta_campaigns_task(self, account_id: str | None = None):
    """
    Sincroniza campanhas + metricas do Meta Ads.
    Se account_id nao for informado, sincroniza todas as contas ativas.
    """
    from core.db import get_supabase
    from modules.ads_manager.services.meta_ads import sync_campaigns

    supabase = get_supabase()
    q = supabase.table("ad_accounts").select("*").eq("plataforma", "meta").eq("status", "ativo")
    if account_id:
        q = q.eq("id", account_id)
    rows = q.execute().data or []

    loop = asyncio.new_event_loop()
    try:
        resultados = []
        for row in rows:
            try:
                r = loop.run_until_complete(sync_campaigns(row))
                resultados.append({"account_id": row["id"], **r})
            except Exception as e:
                logger.exception(f"[ads_manager] sync falhou para {row['id']}: {e}")
                resultados.append({"account_id": row["id"], "erro": str(e)})
        return {"total": len(rows), "resultados": resultados}
    finally:
        loop.close()


@shared_task(name="modules.ads_manager.tasks.run_ad_rules_task")
def run_ad_rules_task(workspace_id: str | None = None):
    """Avalia e executa todas as regras de automacao ativas."""
    from modules.ads_manager.services.rules_engine import run_all_active_rules

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_all_active_rules(workspace_id))
    finally:
        loop.close()
