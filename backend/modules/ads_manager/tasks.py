"""
Tarefas Celery do Ads Manager.
Sessao 8 — Meta Ads.
Sessao 9 — Google Ads + TikTok Ads.
"""

import asyncio
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


def _run_sync_for_platform(plataforma: str, account_id: str | None = None):
    """Generica: sincroniza todas as contas de uma plataforma (ou uma especifica)."""
    from core.db import get_supabase

    if plataforma == "meta":
        from modules.ads_manager.services.meta_ads import sync_campaigns
    elif plataforma == "google":
        from modules.ads_manager.services.google_ads import sync_campaigns
    elif plataforma == "tiktok":
        from modules.ads_manager.services.tiktok_ads import sync_campaigns
    else:
        return {"erro": f"plataforma invalida: {plataforma}"}

    supabase = get_supabase()
    q = supabase.table("ad_accounts").select("*").eq("plataforma", plataforma).eq("status", "ativo")
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
                logger.exception(f"[ads_manager/{plataforma}] sync falhou para {row['id']}: {e}")
                resultados.append({"account_id": row["id"], "erro": str(e)})
        return {"plataforma": plataforma, "total": len(rows), "resultados": resultados}
    finally:
        loop.close()


@shared_task(name="modules.ads_manager.tasks.sync_meta_campaigns_task", bind=True)
def sync_meta_campaigns_task(self, account_id: str | None = None):
    return _run_sync_for_platform("meta", account_id)


@shared_task(name="modules.ads_manager.tasks.sync_google_campaigns_task", bind=True)
def sync_google_campaigns_task(self, account_id: str | None = None):
    return _run_sync_for_platform("google", account_id)


@shared_task(name="modules.ads_manager.tasks.sync_tiktok_campaigns_task", bind=True)
def sync_tiktok_campaigns_task(self, account_id: str | None = None):
    return _run_sync_for_platform("tiktok", account_id)


@shared_task(name="modules.ads_manager.tasks.sync_all_ads_task")
def sync_all_ads_task():
    """Executa sync de todas as plataformas (meta + google + tiktok)."""
    return {
        "meta": _run_sync_for_platform("meta"),
        "google": _run_sync_for_platform("google"),
        "tiktok": _run_sync_for_platform("tiktok"),
    }


@shared_task(name="modules.ads_manager.tasks.run_ad_rules_task")
def run_ad_rules_task(workspace_id: str | None = None):
    """Avalia e executa todas as regras de automacao ativas."""
    from modules.ads_manager.services.rules_engine import run_all_active_rules

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(run_all_active_rules(workspace_id))
    finally:
        loop.close()
