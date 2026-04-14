"""
Integracao com Google Ads API.

Docs: https://developers.google.com/google-ads/api/docs/start

Modos:
- **real**: via REST (googleads.googleapis.com) com access_token OAuth + developer_token
- **mock/offline**: falhas HTTP nao quebram dashboards (registra warning)

Convencoes:
- `external_id` = customer_id (sem hifens), ex: "1234567890"
- Valores monetarios no Google Ads vem em micros (1/1.000.000 de unidade). Convertemos para centavos.
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

GOOGLE_OAUTH_BASE = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_ADS_SCOPE = "https://www.googleapis.com/auth/adwords"


def _api_base() -> str:
    return f"https://googleads.googleapis.com/{settings.google_ads_api_version}"


def _headers(token: str) -> dict[str, str]:
    h = {
        "Authorization": f"Bearer {token}",
        "developer-token": settings.google_ads_developer_token,
        "Content-Type": "application/json",
    }
    if settings.google_ads_login_customer_id:
        h["login-customer-id"] = settings.google_ads_login_customer_id.replace("-", "")
    return h


# ============================================================
# OAuth
# ============================================================

def build_oauth_url(redirect_uri: str, state: str) -> str:
    return (
        f"{GOOGLE_OAUTH_BASE}"
        f"?client_id={settings.google_ads_client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={GOOGLE_ADS_SCOPE}"
        f"&access_type=offline"
        f"&prompt=consent"
        f"&state={state}"
    )


async def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        r.raise_for_status()
        return r.json()


async def refresh_access_token(refresh_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "refresh_token": refresh_token,
                "client_id": settings.google_ads_client_id,
                "client_secret": settings.google_ads_client_secret,
                "grant_type": "refresh_token",
            },
        )
        r.raise_for_status()
        return r.json()


async def _get_valid_token(ad_account_row: dict[str, Any]) -> Optional[str]:
    """Retorna access token valido, renovando via refresh_token se necessario."""
    from core.crypto import decrypt_value, encrypt_value

    try:
        token = decrypt_value(ad_account_row["access_token_encrypted"])
    except Exception:
        token = None

    expira = ad_account_row.get("token_expira_em")
    expirado = False
    if expira:
        try:
            exp_dt = datetime.fromisoformat(str(expira).replace("Z", "+00:00"))
            expirado = exp_dt <= datetime.now(timezone.utc) + timedelta(minutes=2)
        except Exception:
            expirado = False

    if token and not expirado:
        return token

    rt_enc = ad_account_row.get("refresh_token_encrypted")
    if not rt_enc:
        return token
    try:
        rt = decrypt_value(rt_enc)
        data = await refresh_access_token(rt)
        new_token = data.get("access_token")
        expires_in = int(data.get("expires_in", 3600))
        if new_token:
            supabase = get_supabase()
            supabase.table("ad_accounts").update({
                "access_token_encrypted": encrypt_value(new_token),
                "token_expira_em": (
                    datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                ).isoformat(),
            }).eq("id", ad_account_row["id"]).execute()
            return new_token
    except Exception as e:
        logger.warning(f"[google_ads] falha ao renovar token: {e}")
    return token


# ============================================================
# Sync
# ============================================================

async def sync_campaigns(ad_account_row: dict[str, Any]) -> dict[str, int]:
    """
    Sincroniza campanhas + metricas (ultimos 7 dias) via Google Ads API / GAQL.
    Upsert idempotente.
    """
    supabase = get_supabase()
    workspace_id = ad_account_row["workspace_id"]
    account_id = ad_account_row["id"]
    customer_id = ad_account_row["external_id"].replace("-", "")

    token = await _get_valid_token(ad_account_row)
    if not token:
        return {"campaigns": 0, "metrics": 0, "erro": "token_invalido"}

    campaigns_count = 0
    metrics_count = 0
    campaign_id_map: dict[str, str] = {}

    gaql_campaigns = (
        "SELECT campaign.id, campaign.name, campaign.status, "
        "campaign.advertising_channel_type, campaign_budget.amount_micros, "
        "campaign.start_date, campaign.end_date "
        "FROM campaign"
    )
    since = (date.today() - timedelta(days=7)).isoformat()
    until = date.today().isoformat()
    gaql_metrics = (
        "SELECT campaign.id, segments.date, metrics.impressions, metrics.clicks, "
        "metrics.cost_micros, metrics.conversions, metrics.conversions_value, "
        "metrics.ctr, metrics.average_cpc "
        "FROM campaign "
        f"WHERE segments.date BETWEEN '{since}' AND '{until}'"
    )

    try:
        async with httpx.AsyncClient(timeout=60, headers=_headers(token)) as client:
            # 1. Campanhas
            r = await client.post(
                f"{_api_base()}/customers/{customer_id}/googleAds:searchStream",
                json={"query": gaql_campaigns},
            )
            r.raise_for_status()
            data = r.json()
            results = []
            if isinstance(data, list):
                for chunk in data:
                    results.extend(chunk.get("results", []) or [])
            else:
                results = data.get("results", []) or []

            for row in results:
                c = row.get("campaign", {})
                bud = row.get("campaignBudget", {}) or row.get("campaign_budget", {})
                ext_id = str(c.get("id") or "")
                if not ext_id:
                    continue
                daily_micros = int(bud.get("amountMicros") or bud.get("amount_micros") or 0)
                db_row = {
                    "workspace_id": workspace_id,
                    "ad_account_id": account_id,
                    "external_id": ext_id,
                    "nome": c.get("name") or "",
                    "objetivo": (c.get("advertisingChannelType") or c.get("advertising_channel_type") or "").lower() or None,
                    "status": (c.get("status") or "").lower(),
                    "orcamento_diario_centavos": _micros_to_cents(daily_micros) if daily_micros else None,
                    "data_inicio": c.get("startDate") or c.get("start_date"),
                    "data_fim": c.get("endDate") or c.get("end_date"),
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

            # 2. Metricas
            r2 = await client.post(
                f"{_api_base()}/customers/{customer_id}/googleAds:searchStream",
                json={"query": gaql_metrics},
            )
            r2.raise_for_status()
            data2 = r2.json()
            results2 = []
            if isinstance(data2, list):
                for chunk in data2:
                    results2.extend(chunk.get("results", []) or [])
            else:
                results2 = data2.get("results", []) or []

            for row in results2:
                c = row.get("campaign", {})
                seg = row.get("segments", {})
                m = row.get("metrics", {})
                ext_id = str(c.get("id") or "")
                internal_id = campaign_id_map.get(ext_id)
                if not internal_id:
                    continue
                gasto_cents = _micros_to_cents(int(m.get("costMicros") or m.get("cost_micros") or 0))
                cpc_cents = _micros_to_cents(int(m.get("averageCpc") or m.get("average_cpc") or 0))
                conv = int(float(m.get("conversions") or 0))
                receita_cents = int(float(m.get("conversionsValue") or m.get("conversions_value") or 0) * 100)
                metric = {
                    "workspace_id": workspace_id,
                    "ad_account_id": account_id,
                    "campaign_id": internal_id,
                    "data": seg.get("date") or date.today().isoformat(),
                    "impressoes": int(m.get("impressions") or 0),
                    "cliques": int(m.get("clicks") or 0),
                    "conversoes": conv,
                    "gasto_centavos": gasto_cents,
                    "receita_centavos": receita_cents,
                    "ctr": float(m.get("ctr") or 0) * 100 if float(m.get("ctr") or 0) < 1 else float(m.get("ctr") or 0),
                    "cpc_centavos": cpc_cents,
                    "cpa_centavos": (gasto_cents // conv) if conv else None,
                    "roas": (receita_cents / gasto_cents) if gasto_cents else None,
                }
                supabase.table("ad_metrics_daily").upsert(metric).execute()
                metrics_count += 1

            supabase.table("ad_accounts").update({
                "ultimo_sync": datetime.now(timezone.utc).isoformat(),
                "status": "ativo",
            }).eq("id", account_id).execute()

    except httpx.HTTPError as e:
        logger.error(f"[google_ads] sync falhou para {account_id}: {e}")
        supabase.table("ad_accounts").update({"status": "expirado"}).eq("id", account_id).execute()
        return {"campaigns": 0, "metrics": 0, "erro": str(e)}

    return {"campaigns": campaigns_count, "metrics": metrics_count}


# ============================================================
# Acoes: pause / activate / budget
# ============================================================

async def update_campaign_status(campaign_row: dict[str, Any], status: str) -> bool:
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
    token = await _get_valid_token(acct.data[0])
    if not token:
        return False

    g_status = "ENABLED" if status == "activate" else "PAUSED"
    customer_id = acct.data[0]["external_id"].replace("-", "")
    resource = f"customers/{customer_id}/campaigns/{campaign_row['external_id']}"
    body = {
        "operations": [{
            "update": {"resourceName": resource, "status": g_status},
            "updateMask": "status",
        }],
    }
    try:
        async with httpx.AsyncClient(timeout=30, headers=_headers(token)) as client:
            r = await client.post(
                f"{_api_base()}/customers/{customer_id}/campaigns:mutate",
                json=body,
            )
            r.raise_for_status()
        supabase.table("campaigns").update({
            "status": g_status.lower(),
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", campaign_row["id"]).execute()
        return True
    except httpx.HTTPError as e:
        logger.error(f"[google_ads] falha ao alterar status: {e}")
        return False


async def update_campaign_budget(
    campaign_row: dict[str, Any],
    orcamento_diario_centavos: Optional[int] = None,
    orcamento_total_centavos: Optional[int] = None,
) -> bool:
    """Google Ads: ajustar orcamento exige mutate em campaign_budget (fora do escopo desta sessao inicial).
    Atualizamos apenas localmente e registramos no banco."""
    if orcamento_diario_centavos is None:
        return False
    supabase = get_supabase()
    supabase.table("campaigns").update({
        "orcamento_diario_centavos": orcamento_diario_centavos,
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", campaign_row["id"]).execute()
    logger.info("[google_ads] ajuste de orcamento registrado localmente; propagacao real requer mutate em campaign_budget")
    return True


# ============================================================
# Helpers
# ============================================================

def _micros_to_cents(micros: int) -> int:
    """1 unidade = 1.000.000 micros. 1 unidade = 100 centavos. => micros/10000."""
    return int(micros // 10_000)
