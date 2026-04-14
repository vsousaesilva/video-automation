"""
Ads Manager — Meta Ads (Facebook + Instagram).

Endpoints:
  GET    /ads/oauth/meta/url                — URL de inicio do OAuth Meta
  POST   /ads/accounts/connect              — vincular conta Meta Ads (apos OAuth)
  GET    /ads/accounts                      — listar contas vinculadas
  DELETE /ads/accounts/{id}                 — desvincular conta
  POST   /ads/accounts/{id}/sync            — disparar sync manual
  GET    /ads/campaigns                     — listar campanhas
  POST   /ads/campaigns/{id}/action         — pause / activate
  PATCH  /ads/campaigns/{id}/budget         — ajustar orcamento
  GET    /ads/metrics                       — metricas agregadas
  GET    /ads/rules                         — listar regras
  POST   /ads/rules                         — criar regra
  PUT    /ads/rules/{id}                    — atualizar regra
  DELETE /ads/rules/{id}                    — remover regra
  POST   /ads/rules/{id}/run                — executar regra agora
"""

import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.db import get_supabase
from core.crypto import encrypt_value
from core.billing import get_workspace_subscription
from modules.ads_manager.schemas import (
    AdAccountConnect,
    AdAccountUpdate,
    CampaignAction,
    CampaignBudgetUpdate,
    AdRuleCreate,
    AdRuleUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ads", tags=["Ads Manager"])


def _ensure_pro_plan(workspace_id: str) -> None:
    """Ads Manager e limitado a planos Pro/Enterprise."""
    sub = get_workspace_subscription(workspace_id)
    slug = (sub or {}).get("plans", {}).get("slug", "").lower() if sub else ""
    if slug not in ("pro", "enterprise"):
        raise HTTPException(
            status_code=403,
            detail="Ads Manager disponivel apenas nos planos Pro e Enterprise.",
        )


# ============================================================
# OAuth
# ============================================================

@router.get("/oauth/meta/url")
async def meta_oauth_url(
    redirect_uri: str = Query(..., description="URL de callback registrada no app Meta"),
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    from modules.ads_manager.services.meta_ads import build_oauth_url
    import secrets
    state = secrets.token_urlsafe(16)
    return {"url": build_oauth_url(redirect_uri, state), "state": state}


# ============================================================
# Contas
# ============================================================

@router.post("/accounts/connect")
async def connect_account(
    body: AdAccountConnect,
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    encrypted = encrypt_value(body.access_token)

    data = {
        "workspace_id": workspace_id,
        "plataforma": body.plataforma.value,
        "external_id": body.external_id,
        "nome": body.nome,
        "moeda": body.moeda or "BRL",
        "fuso": body.fuso,
        "access_token_encrypted": encrypted,
        "token_expira_em": body.token_expira_em,
        "refresh_token_encrypted": encrypt_value(body.refresh_token) if body.refresh_token else None,
        "status": "ativo",
    }

    result = (
        supabase.table("ad_accounts")
        .upsert(data, on_conflict="workspace_id,plataforma,external_id")
        .execute()
    )
    row = result.data[0] if result.data else data
    row.pop("access_token_encrypted", None)
    row.pop("refresh_token_encrypted", None)
    return row


@router.get("/accounts")
async def list_accounts(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = (
        supabase.table("ad_accounts")
        .select("id,plataforma,external_id,nome,moeda,fuso,status,ultimo_sync,criado_em")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
        .execute()
    )
    return result.data or []


@router.put("/accounts/{account_id}")
async def update_account(
    account_id: str,
    body: AdAccountUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    update = body.model_dump(exclude_none=True)
    if body.status:
        update["status"] = body.status.value
    update["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("ad_accounts")
        .update(update)
        .eq("id", account_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Conta nao encontrada")
    row = result.data[0]
    row.pop("access_token_encrypted", None)
    row.pop("refresh_token_encrypted", None)
    return row


@router.delete("/accounts/{account_id}")
async def delete_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = (
        supabase.table("ad_accounts")
        .delete()
        .eq("id", account_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Conta nao encontrada")
    return {"detail": "Conta desvinculada"}


@router.post("/accounts/{account_id}/sync")
async def sync_account(
    account_id: str,
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    supabase = get_supabase()
    acct = (
        supabase.table("ad_accounts")
        .select("*")
        .eq("id", account_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not acct.data:
        raise HTTPException(404, "Conta nao encontrada")
    row = acct.data[0]
    if row["plataforma"] != "meta":
        raise HTTPException(400, f"Sync ainda nao suportado para {row['plataforma']}")
    from modules.ads_manager.services.meta_ads import sync_campaigns
    result = await sync_campaigns(row)
    return {"conta_id": account_id, **result}


# ============================================================
# Campanhas
# ============================================================

@router.get("/campaigns")
async def list_campaigns(
    current_user: dict = Depends(get_current_user),
    ad_account_id: str = Query(None),
    status: str = Query(None),
):
    supabase = get_supabase()
    q = (
        supabase.table("campaigns")
        .select("*, ad_accounts(id, nome, plataforma, moeda)")
        .eq("workspace_id", current_user["workspace_id"])
        .order("atualizado_em", desc=True)
    )
    if ad_account_id:
        q = q.eq("ad_account_id", ad_account_id)
    if status:
        q = q.eq("status", status)
    return q.execute().data or []


@router.post("/campaigns/{campaign_id}/action")
async def campaign_action(
    campaign_id: str,
    body: CampaignAction,
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    supabase = get_supabase()
    camp = (
        supabase.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not camp.data:
        raise HTTPException(404, "Campanha nao encontrada")
    from modules.ads_manager.services.meta_ads import update_campaign_status
    ok = await update_campaign_status(camp.data[0], body.action)
    if not ok:
        raise HTTPException(502, "Falha ao comunicar com o Meta Ads")
    return {"detail": f"Campanha {body.action} aplicado", "campaign_id": campaign_id}


@router.patch("/campaigns/{campaign_id}/budget")
async def campaign_budget(
    campaign_id: str,
    body: CampaignBudgetUpdate,
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    supabase = get_supabase()
    camp = (
        supabase.table("campaigns")
        .select("*")
        .eq("id", campaign_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not camp.data:
        raise HTTPException(404, "Campanha nao encontrada")
    from modules.ads_manager.services.meta_ads import update_campaign_budget
    ok = await update_campaign_budget(
        camp.data[0],
        orcamento_diario_centavos=body.orcamento_diario_centavos,
        orcamento_total_centavos=body.orcamento_total_centavos,
    )
    if not ok:
        raise HTTPException(502, "Falha ao comunicar com o Meta Ads")
    return {"detail": "Orcamento atualizado"}


# ============================================================
# Metricas
# ============================================================

@router.get("/metrics")
async def metrics_summary(
    current_user: dict = Depends(get_current_user),
    desde: str = Query(None, description="YYYY-MM-DD (padrao: 30 dias atras)"),
    ate: str = Query(None),
    campaign_id: str = Query(None),
    ad_account_id: str = Query(None),
):
    """Agrega metricas por dia para graficos + totais."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    if not desde:
        desde = (date.today() - timedelta(days=30)).isoformat()
    if not ate:
        ate = date.today().isoformat()

    q = (
        supabase.table("ad_metrics_daily")
        .select("*")
        .eq("workspace_id", workspace_id)
        .gte("data", desde)
        .lte("data", ate)
        .order("data")
    )
    if campaign_id:
        q = q.eq("campaign_id", campaign_id)
    if ad_account_id:
        q = q.eq("ad_account_id", ad_account_id)
    rows = q.execute().data or []

    # Agrupar por dia
    por_dia: dict[str, dict[str, int | float]] = {}
    totais = {"impressoes": 0, "cliques": 0, "conversoes": 0,
              "gasto_centavos": 0, "receita_centavos": 0}
    for r in rows:
        d = r.get("data")
        if not d:
            continue
        bucket = por_dia.setdefault(d, {
            "data": d, "impressoes": 0, "cliques": 0,
            "conversoes": 0, "gasto_centavos": 0, "receita_centavos": 0,
        })
        for k in ("impressoes", "cliques", "conversoes", "gasto_centavos", "receita_centavos"):
            bucket[k] = (bucket.get(k) or 0) + (r.get(k) or 0)
            totais[k] += (r.get(k) or 0)

    cpa = (totais["gasto_centavos"] // totais["conversoes"]) if totais["conversoes"] else 0
    roas = (totais["receita_centavos"] / totais["gasto_centavos"]) if totais["gasto_centavos"] else 0.0
    ctr = (totais["cliques"] / totais["impressoes"] * 100) if totais["impressoes"] else 0.0

    return {
        "periodo": {"desde": desde, "ate": ate},
        "totais": {
            **totais,
            "cpa_centavos": cpa,
            "roas": round(roas, 4),
            "ctr": round(ctr, 2),
        },
        "serie": sorted(por_dia.values(), key=lambda x: x["data"]),
    }


# ============================================================
# Regras de automacao
# ============================================================

@router.get("/rules")
async def list_rules(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = (
        supabase.table("ad_rules")
        .select("*")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
        .execute()
    )
    return result.data or []


@router.post("/rules")
async def create_rule(
    body: AdRuleCreate,
    current_user: dict = Depends(get_current_user),
):
    _ensure_pro_plan(current_user["workspace_id"])
    supabase = get_supabase()
    data = {
        "workspace_id": current_user["workspace_id"],
        "ad_account_id": body.ad_account_id,
        "nome": body.nome,
        "escopo": body.escopo.value,
        "escopo_ids": body.escopo_ids,
        "condicao": body.condicao.model_dump(),
        "acao": body.acao.value,
        "acao_params": body.acao_params,
        "ativa": body.ativa,
    }
    result = supabase.table("ad_rules").insert(data).execute()
    return result.data[0]


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    body: AdRuleUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    update = body.model_dump(exclude_none=True)
    if body.condicao:
        update["condicao"] = body.condicao.model_dump()
    if body.acao:
        update["acao"] = body.acao.value
    update["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("ad_rules")
        .update(update)
        .eq("id", rule_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Regra nao encontrada")
    return result.data[0]


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = (
        supabase.table("ad_rules")
        .delete()
        .eq("id", rule_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Regra nao encontrada")
    return {"detail": "Regra removida"}


@router.post("/rules/{rule_id}/run")
async def run_rule(
    rule_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    r = (
        supabase.table("ad_rules")
        .select("*")
        .eq("id", rule_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not r.data:
        raise HTTPException(404, "Regra nao encontrada")
    from modules.ads_manager.services.rules_engine import execute_rule
    return await execute_rule(r.data[0])
