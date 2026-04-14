"""
Integracao com Meta Marketing API (Facebook + Instagram Ads).

Docs: https://developers.facebook.com/docs/marketing-apis/

O servico opera em dois modos:
- **real**: com access_token da conta conectada, chama API v20.0
- **mock/offline**: se a chamada HTTP falhar ou nao houver token valido, o sync
  retorna sem erro e registra warning (para nao quebrar dashboards).
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

META_API_VERSION = "v20.0"
META_API_BASE = f"https://graph.facebook.com/{META_API_VERSION}"


# ============================================================
# OAuth / Token
# ============================================================

def build_oauth_url(redirect_uri: str, state: str) -> str:
    """Retorna URL para iniciar OAuth do Meta Ads."""
    scope = "ads_management,ads_read,business_management"
    return (
        f"https://www.facebook.com/{META_API_VERSION}/dialog/oauth"
        f"?client_id={settings.meta_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&scope={scope}"
        f"&state={state}"
        f"&response_type=code"
    )


async def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    """Troca code por access_token (long-lived)."""
    async with httpx.AsyncClient(timeout=30) as client:
        # 1. Short-lived token
        short = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        short.raise_for_status()
        short_data = short.json()

        # 2. Long-lived token (60 dias)
        long = await client.get(
            f"{META_API_BASE}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": short_data["access_token"],
            },
        )
        long.raise_for_status()
        return long.json()


async def list_ad_accounts(access_token: str) -> list[dict[str, Any]]:
    """Lista contas de anuncios acessiveis pelo token."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{META_API_BASE}/me/adaccounts",
            params={
                "access_token": access_token,
                "fields": "id,account_id,name,currency,timezone_name,account_status",
            },
        )
        r.raise_for_status()
        return r.json().get("data", [])


# ============================================================
# Sync de campanhas
# ============================================================

async def sync_campaigns(ad_account_row: dict[str, Any]) -> dict[str, int]:
    """
    Sincroniza campanhas + ad_sets + ads + insights dos ultimos 7 dias
    para uma conta vinculada. Faz upsert idempotente.
    """
    from core.crypto import decrypt_value

    supabase = get_supabase()
    workspace_id = ad_account_row["workspace_id"]
    account_id = ad_account_row["id"]
    external_id = ad_account_row["external_id"]

    try:
        token = decrypt_value(ad_account_row["access_token_encrypted"])
    except Exception as e:
        logger.warning(f"[meta_ads] token invalido para conta {account_id}: {e}")
        return {"campaigns": 0, "ad_sets": 0, "metrics": 0, "erro": "token_invalido"}

    campaigns_count = 0
    ad_sets_count = 0
    metrics_count = 0

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            # 1. Campanhas
            r = await client.get(
                f"{META_API_BASE}/{external_id}/campaigns",
                params={
                    "access_token": token,
                    "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time",
                    "limit": 100,
                },
            )
            r.raise_for_status()
            campaigns = r.json().get("data", [])

            campaign_id_map: dict[str, str] = {}  # external_id -> uuid
            for c in campaigns:
                row = {
                    "workspace_id": workspace_id,
                    "ad_account_id": account_id,
                    "external_id": c["id"],
                    "nome": c.get("name", ""),
                    "objetivo": c.get("objective"),
                    "status": (c.get("status") or "").lower(),
                    "orcamento_diario_centavos": _parse_money(c.get("daily_budget")),
                    "orcamento_total_centavos": _parse_money(c.get("lifetime_budget")),
                    "data_inicio": _parse_date(c.get("start_time")),
                    "data_fim": _parse_date(c.get("stop_time")),
                    "atualizado_em": datetime.now(timezone.utc).isoformat(),
                }
                up = (
                    supabase.table("campaigns")
                    .upsert(row, on_conflict="ad_account_id,external_id")
                    .execute()
                )
                if up.data:
                    campaign_id_map[c["id"]] = up.data[0]["id"]
                    campaigns_count += 1

            # 2. Insights dos ultimos 7 dias (por campanha)
            since = (date.today() - timedelta(days=7)).isoformat()
            until = date.today().isoformat()

            for ext_id, internal_id in campaign_id_map.items():
                try:
                    ins = await client.get(
                        f"{META_API_BASE}/{ext_id}/insights",
                        params={
                            "access_token": token,
                            "time_range": f'{{"since":"{since}","until":"{until}"}}',
                            "time_increment": 1,
                            "fields": "impressions,clicks,spend,ctr,cpc,cpp,actions,date_start",
                        },
                    )
                    ins.raise_for_status()
                    for row in ins.json().get("data", []):
                        metric = _build_metric_row(
                            workspace_id=workspace_id,
                            ad_account_id=account_id,
                            campaign_id=internal_id,
                            insight=row,
                        )
                        supabase.table("ad_metrics_daily").upsert(metric).execute()
                        metrics_count += 1
                except httpx.HTTPError as e:
                    logger.warning(f"[meta_ads] insight falhou para {ext_id}: {e}")

            supabase.table("ad_accounts").update({
                "ultimo_sync": datetime.now(timezone.utc).isoformat(),
                "status": "ativo",
            }).eq("id", account_id).execute()

    except httpx.HTTPError as e:
        logger.error(f"[meta_ads] sync falhou para {account_id}: {e}")
        supabase.table("ad_accounts").update({"status": "expirado"}).eq("id", account_id).execute()
        return {"campaigns": 0, "ad_sets": 0, "metrics": 0, "erro": str(e)}

    return {
        "campaigns": campaigns_count,
        "ad_sets": ad_sets_count,
        "metrics": metrics_count,
    }


# ============================================================
# Acoes: pausar / ativar / ajustar orcamento
# ============================================================

async def update_campaign_status(campaign_row: dict[str, Any], status: str) -> bool:
    """Atualiza status (ACTIVE / PAUSED) de uma campanha no Meta."""
    from core.crypto import decrypt_value as _decrypt

    supabase = get_supabase()
    acct = (
        supabase.table("ad_accounts")
        .select("access_token_encrypted")
        .eq("id", campaign_row["ad_account_id"])
        .limit(1)
        .execute()
    )
    if not acct.data:
        return False

    try:
        token = _decrypt(acct.data[0]["access_token_encrypted"])
    except Exception:
        return False

    meta_status = "ACTIVE" if status == "activate" else "PAUSED"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{META_API_BASE}/{campaign_row['external_id']}",
                params={"access_token": token, "status": meta_status},
            )
            r.raise_for_status()
        supabase.table("campaigns").update({
            "status": meta_status.lower(),
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_row["id"]).execute()
        return True
    except httpx.HTTPError as e:
        logger.error(f"[meta_ads] falha ao alterar status: {e}")
        return False


async def update_campaign_budget(
    campaign_row: dict[str, Any],
    orcamento_diario_centavos: Optional[int] = None,
    orcamento_total_centavos: Optional[int] = None,
) -> bool:
    from core.crypto import decrypt_value as _decrypt

    supabase = get_supabase()
    acct = (
        supabase.table("ad_accounts")
        .select("access_token_encrypted")
        .eq("id", campaign_row["ad_account_id"])
        .limit(1)
        .execute()
    )
    if not acct.data:
        return False
    try:
        token = _decrypt(acct.data[0]["access_token_encrypted"])
    except Exception:
        return False

    params: dict[str, Any] = {"access_token": token}
    if orcamento_diario_centavos is not None:
        params["daily_budget"] = orcamento_diario_centavos  # Meta usa centavos
    if orcamento_total_centavos is not None:
        params["lifetime_budget"] = orcamento_total_centavos
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{META_API_BASE}/{campaign_row['external_id']}", params=params
            )
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
        logger.error(f"[meta_ads] falha ao ajustar orcamento: {e}")
        return False


# ============================================================
# Helpers
# ============================================================

def _parse_money(v: Any) -> Optional[int]:
    """Meta retorna budget como string em centavos (ex: '10000' = R$ 100,00)."""
    if v is None:
        return None
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def _parse_date(v: Any) -> Optional[str]:
    if not v:
        return None
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return None


def _build_metric_row(
    workspace_id: str,
    ad_account_id: str,
    campaign_id: str,
    insight: dict[str, Any],
) -> dict[str, Any]:
    spend_cents = int(float(insight.get("spend", 0) or 0) * 100)
    clicks = int(insight.get("clicks", 0) or 0)
    impressions = int(insight.get("impressions", 0) or 0)

    # Conversoes via actions (Meta retorna lista)
    conversoes = 0
    for a in insight.get("actions", []) or []:
        if a.get("action_type") in ("purchase", "lead", "complete_registration"):
            conversoes += int(a.get("value", 0) or 0)

    return {
        "workspace_id": workspace_id,
        "ad_account_id": ad_account_id,
        "campaign_id": campaign_id,
        "data": insight.get("date_start") or date.today().isoformat(),
        "impressoes": impressions,
        "cliques": clicks,
        "conversoes": conversoes,
        "gasto_centavos": spend_cents,
        "ctr": float(insight.get("ctr", 0) or 0),
        "cpc_centavos": int(float(insight.get("cpc", 0) or 0) * 100),
        "cpa_centavos": (spend_cents // conversoes) if conversoes else None,
    }
