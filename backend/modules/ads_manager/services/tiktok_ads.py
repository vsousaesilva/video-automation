"""
Integracao com TikTok Marketing API.

Docs: https://business-api.tiktok.com/portal/docs

Convencoes:
- `external_id` = advertiser_id
- Valores monetarios no TikTok sao em unidades (ex: 10.50) => convertemos para centavos (*100)
- Status TikTok: STATUS_DISABLE (paused) / STATUS_ENABLE (active)
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

import httpx

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()


def _base() -> str:
    return settings.tiktok_ads_api_base.rstrip("/")


def _headers(token: str) -> dict[str, str]:
    return {"Access-Token": token, "Content-Type": "application/json"}


# ============================================================
# OAuth
# ============================================================

def build_oauth_url(redirect_uri: str, state: str) -> str:
    return (
        "https://business-api.tiktok.com/portal/auth"
        f"?app_id={settings.tiktok_ads_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
    )


async def exchange_code_for_token(auth_code: str) -> dict[str, Any]:
    """Troca auth_code pelo access_token (long-lived) do TikTok Marketing API."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{_base()}/oauth2/access_token/",
            json={
                "app_id": settings.tiktok_ads_app_id,
                "secret": settings.tiktok_ads_app_secret,
                "auth_code": auth_code,
            },
        )
        r.raise_for_status()
        payload = r.json() or {}
        if payload.get("code") not in (0, None):
            raise httpx.HTTPError(f"TikTok OAuth falhou: {payload}")
        return payload.get("data") or {}


async def list_advertisers(access_token: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{_base()}/oauth2/advertiser/get/",
            params={
                "app_id": settings.tiktok_ads_app_id,
                "secret": settings.tiktok_ads_app_secret,
                "access_token": access_token,
            },
        )
        r.raise_for_status()
        return (r.json() or {}).get("data", {}).get("list", []) or []


# ============================================================
# Sync
# ============================================================

async def sync_campaigns(ad_account_row: dict[str, Any]) -> dict[str, int]:
    """Sincroniza campanhas + metricas dos ultimos 7 dias via TikTok Marketing API."""
    from core.crypto import decrypt_value

    supabase = get_supabase()
    workspace_id = ad_account_row["workspace_id"]
    account_id = ad_account_row["id"]
    advertiser_id = ad_account_row["external_id"]

    try:
        token = decrypt_value(ad_account_row["access_token_encrypted"])
    except Exception as e:
        logger.warning(f"[tiktok_ads] token invalido para conta {account_id}: {e}")
        return {"campaigns": 0, "metrics": 0, "erro": "token_invalido"}

    campaigns_count = 0
    metrics_count = 0
    campaign_id_map: dict[str, str] = {}

    try:
        async with httpx.AsyncClient(timeout=60, headers=_headers(token)) as client:
            # 1. Campanhas
            r = await client.get(
                f"{_base()}/campaign/get/",
                params={
                    "advertiser_id": advertiser_id,
                    "page_size": 100,
                },
            )
            r.raise_for_status()
            payload = r.json() or {}
            items = (payload.get("data") or {}).get("list", []) or []

            for c in items:
                ext_id = str(c.get("campaign_id"))
                budget = c.get("budget") or 0
                status_raw = (c.get("secondary_status") or c.get("operation_status") or "").upper()
                status_norm = _normalize_status(status_raw)
                db_row = {
                    "workspace_id": workspace_id,
                    "ad_account_id": account_id,
                    "external_id": ext_id,
                    "nome": c.get("campaign_name") or "",
                    "objetivo": (c.get("objective_type") or "").lower() or None,
                    "status": status_norm,
                    "orcamento_diario_centavos": int(float(budget) * 100) if (c.get("budget_mode") == "BUDGET_MODE_DAY") else None,
                    "orcamento_total_centavos": int(float(budget) * 100) if (c.get("budget_mode") == "BUDGET_MODE_TOTAL") else None,
                    "data_inicio": c.get("create_time", "")[:10] or None,
                    "atualizado_em": datetime.now(timezone.utc).isoformat(),
                }
                up = (
                    supabase.table("campaigns")
                    .upsert(db_row, on_conflict="ad_account_id,external_id")
                    .execute()
                )
                if up.data:
                    campaign_id_map[ext_id] = up.data[0]["id"]
                    campaigns_count += 1

            # 2. Relatorio diario por campanha
            since = (date.today() - timedelta(days=7)).isoformat()
            until = date.today().isoformat()

            for ext_id, internal_id in campaign_id_map.items():
                try:
                    rep = await client.get(
                        f"{_base()}/report/integrated/get/",
                        params={
                            "advertiser_id": advertiser_id,
                            "report_type": "BASIC",
                            "data_level": "AUCTION_CAMPAIGN",
                            "dimensions": '["campaign_id","stat_time_day"]',
                            "metrics": '["impressions","clicks","spend","conversion","ctr","cpc","cost_per_conversion"]',
                            "start_date": since,
                            "end_date": until,
                            "filters": f'[{{"field_name":"campaign_ids","filter_type":"IN","filter_value":"[\\"{ext_id}\\"]"}}]',
                            "page_size": 100,
                        },
                    )
                    rep.raise_for_status()
                    rep_data = (rep.json() or {}).get("data", {}).get("list", []) or []
                    for row in rep_data:
                        dims = row.get("dimensions", {}) or {}
                        m = row.get("metrics", {}) or {}
                        spend_cents = int(float(m.get("spend") or 0) * 100)
                        clicks = int(float(m.get("clicks") or 0))
                        impr = int(float(m.get("impressions") or 0))
                        conv = int(float(m.get("conversion") or 0))
                        cpc_cents = int(float(m.get("cpc") or 0) * 100)
                        metric = {
                            "workspace_id": workspace_id,
                            "ad_account_id": account_id,
                            "campaign_id": internal_id,
                            "data": dims.get("stat_time_day", "")[:10] or date.today().isoformat(),
                            "impressoes": impr,
                            "cliques": clicks,
                            "conversoes": conv,
                            "gasto_centavos": spend_cents,
                            "ctr": float(m.get("ctr") or 0),
                            "cpc_centavos": cpc_cents,
                            "cpa_centavos": int(float(m.get("cost_per_conversion") or 0) * 100) or None,
                        }
                        supabase.table("ad_metrics_daily").upsert(metric).execute()
                        metrics_count += 1
                except httpx.HTTPError as e:
                    logger.warning(f"[tiktok_ads] relatorio falhou para {ext_id}: {e}")

            supabase.table("ad_accounts").update({
                "ultimo_sync": datetime.now(timezone.utc).isoformat(),
                "status": "ativo",
            }).eq("id", account_id).execute()

    except httpx.HTTPError as e:
        logger.error(f"[tiktok_ads] sync falhou para {account_id}: {e}")
        supabase.table("ad_accounts").update({"status": "expirado"}).eq("id", account_id).execute()
        return {"campaigns": 0, "metrics": 0, "erro": str(e)}

    return {"campaigns": campaigns_count, "metrics": metrics_count}


# ============================================================
# Acoes
# ============================================================

async def update_campaign_status(campaign_row: dict[str, Any], status: str) -> bool:
    from core.crypto import decrypt_value

    supabase = get_supabase()
    acct = (
        supabase.table("ad_accounts")
        .select("*")
        .eq("id", campaign_row["ad_account_id"])
        .limit(1)
        .execute()
    )
    if not acct.data:
        return False
    try:
        token = decrypt_value(acct.data[0]["access_token_encrypted"])
    except Exception:
        return False

    advertiser_id = acct.data[0]["external_id"]
    operation = "ENABLE" if status == "activate" else "DISABLE"
    body = {
        "advertiser_id": advertiser_id,
        "campaign_ids": [campaign_row["external_id"]],
        "operation_status": operation,
    }
    try:
        async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:
            r = await client.post(f"{_base()}/campaign/status/update/", json=body)
            r.raise_for_status()
        supabase.table("campaigns").update({
            "status": "active" if operation == "ENABLE" else "paused",
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_row["id"]).execute()
        return True
    except httpx.HTTPError as e:
        logger.error(f"[tiktok_ads] falha ao alterar status: {e}")
        return False


async def update_campaign_budget(
    campaign_row: dict[str, Any],
    orcamento_diario_centavos: Optional[int] = None,
    orcamento_total_centavos: Optional[int] = None,
) -> bool:
    from core.crypto import decrypt_value

    supabase = get_supabase()
    acct = (
        supabase.table("ad_accounts")
        .select("*")
        .eq("id", campaign_row["ad_account_id"])
        .limit(1)
        .execute()
    )
    if not acct.data:
        return False
    try:
        token = decrypt_value(acct.data[0]["access_token_encrypted"])
    except Exception:
        return False

    body: dict[str, Any] = {
        "advertiser_id": acct.data[0]["external_id"],
        "campaign_id": campaign_row["external_id"],
    }
    if orcamento_diario_centavos is not None:
        body["budget"] = round(orcamento_diario_centavos / 100, 2)
        body["budget_mode"] = "BUDGET_MODE_DAY"
    elif orcamento_total_centavos is not None:
        body["budget"] = round(orcamento_total_centavos / 100, 2)
        body["budget_mode"] = "BUDGET_MODE_TOTAL"
    else:
        return False

    try:
        async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:
            r = await client.post(f"{_base()}/campaign/update/", json=body)
            r.raise_for_status()
        update_data: dict[str, Any] = {
            "atualizado_em": datetime.now(timezone.utc).isoformat()
        }
        if orcamento_diario_centavos is not None:
            update_data["orcamento_diario_centavos"] = orcamento_diario_centavos
        if orcamento_total_centavos is not None:
            update_data["orcamento_total_centavos"] = orcamento_total_centavos
        supabase.table("campaigns").update(update_data).eq("id", campaign_row["id"]).execute()
        return True
    except httpx.HTTPError as e:
        logger.error(f"[tiktok_ads] falha ao ajustar orcamento: {e}")
        return False


# ============================================================
# Helpers
# ============================================================

def _normalize_status(s: str) -> str:
    s = s.upper()
    if "DELETE" in s:
        return "deleted"
    if "DISABLE" in s or "PAUSED" in s:
        return "paused"
    if "ENABLE" in s or "DELIVERY_OK" in s or "ACTIVE" in s:
        return "active"
    return s.lower() or "unknown"
