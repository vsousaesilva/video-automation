"""
Ads Manager — Meta / Google / TikTok Ads (cross-platform).

Endpoints:
  GET    /ads/oauth/{plataforma}/url        — URL de inicio do OAuth (meta|google|tiktok)
  POST   /ads/oauth/{plataforma}/callback   — troca code por token e vincula conta
  POST   /ads/accounts/connect              — vincular conta manualmente (token direto)
  GET    /ads/accounts                      — listar contas (filtro por plataforma)
  DELETE /ads/accounts/{id}                 — desvincular conta
  POST   /ads/accounts/{id}/sync            — disparar sync manual (roteado por plataforma)
  GET    /ads/campaigns                     — listar campanhas (cross-platform)
  POST   /ads/campaigns/{id}/action         — pause / activate
  PATCH  /ads/campaigns/{id}/budget         — ajustar orcamento
  GET    /ads/metrics                       — metricas agregadas (filtro plataforma)
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


VALID_PLATFORMS = {"meta", "google", "tiktok"}


def _get_service(plataforma: str):
    """Retorna o modulo de servico correspondente a plataforma."""
    if plataforma == "meta":
        from modules.ads_manager.services import meta_ads as svc
        return svc
    if plataforma == "google":
        from modules.ads_manager.services import google_ads as svc
        return svc
    if plataforma == "tiktok":
        from modules.ads_manager.services import tiktok_ads as svc
        return svc
    raise HTTPException(400, f"Plataforma '{plataforma}' nao suportada")


# ============================================================
# OAuth
# ============================================================

@router.get("/oauth/{plataforma}/url")
async def oauth_url(
    plataforma: str,
    redirect_uri: str = Query(..., description="URL de callback registrada no app da plataforma"),
    current_user: dict = Depends(get_current_user),
):
    if plataforma not in VALID_PLATFORMS:
        raise HTTPException(400, f"Plataforma invalida: {plataforma}")
    _ensure_pro_plan(current_user["workspace_id"])
    import secrets
    state = secrets.token_urlsafe(16)
    svc = _get_service(plataforma)
    return {"url": svc.build_oauth_url(redirect_uri, state), "state": state, "plataforma": plataforma}


@router.post("/oauth/{plataforma}/callback")
async def oauth_callback(
    plataforma: str,
    code: str = Query(...),
    redirect_uri: str = Query(""),
    external_id: str = Query("", description="Opcional: ad_account/customer/advertiser id"),
    current_user: dict = Depends(get_current_user),
):
    """Troca code por access_token e vincula a conta."""
    if plataforma not in VALID_PLATFORMS:
        raise HTTPException(400, f"Plataforma invalida: {plataforma}")
    _ensure_pro_plan(current_user["workspace_id"])
    svc = _get_service(plataforma)
    supabase = get_supabase()

    try:
        if plataforma == "meta":
            data = await svc.exchange_code_for_token(code, redirect_uri)
        elif plataforma == "google":
            data = await svc.exchange_code_for_token(code, redirect_uri)
        else:  # tiktok
            data = await svc.exchange_code_for_token(code)
    except Exception as e:
        raise HTTPException(502, f"OAuth falhou: {e}")

    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(502, "Token nao retornado pela plataforma")

    expires_in = int(data.get("expires_in", 0) or 0)
    expira_em = (
        (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()
        if expires_in
        else None
    )
    refresh_token = data.get("refresh_token")

    ext = external_id
    if not ext:
        # TikTok retorna advertiser_ids diretamente
        ids = data.get("advertiser_ids") or []
        if ids:
            ext = str(ids[0])
    if not ext:
        raise HTTPException(400, "external_id nao fornecido; informe via query param apos escolher a conta")

    row = {
        "workspace_id": current_user["workspace_id"],
        "plataforma": plataforma,
        "external_id": ext,
        "access_token_encrypted": encrypt_value(access_token),
        "refresh_token_encrypted": encrypt_value(refresh_token) if refresh_token else None,
        "token_expira_em": expira_em,
        "status": "ativo",
    }
    result = (
        supabase.table("ad_accounts")
        .upsert(row, on_conflict="workspace_id,plataforma,external_id")
        .execute()
    )
    out = result.data[0] if result.data else row
    out.pop("access_token_encrypted", None)
    out.pop("refresh_token_encrypted", None)
    return out


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
async def list_accounts(
    current_user: dict = Depends(get_current_user),
    plataforma: str = Query(None, description="Filtrar por plataforma (meta|google|tiktok)"),
):
    supabase = get_supabase()
    q = (
        supabase.table("ad_accounts")
        .select("id,plataforma,external_id,nome,moeda,fuso,status,ultimo_sync,criado_em")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
    )
    if plataforma:
        q = q.eq("plataforma", plataforma)
    return q.execute().data or []


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
    svc = _get_service(row["plataforma"])
    result = await svc.sync_campaigns(row)
    return {"conta_id": account_id, "plataforma": row["plataforma"], **result}


# ============================================================
# Campanhas
# ============================================================

@router.get("/campaigns")
async def list_campaigns(
    current_user: dict = Depends(get_current_user),
    ad_account_id: str = Query(None),
    plataforma: str = Query(None, description="Filtrar por plataforma"),
    status: str = Query(None),
):
    supabase = get_supabase()
    q = (
        supabase.table("campaigns")
        .select("*, ad_accounts!inner(id, nome, plataforma, moeda)")
        .eq("workspace_id", current_user["workspace_id"])
        .order("atualizado_em", desc=True)
    )
    if ad_account_id:
        q = q.eq("ad_account_id", ad_account_id)
    if plataforma:
        q = q.eq("ad_accounts.plataforma", plataforma)
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
        .select("*, ad_accounts(plataforma)")
        .eq("id", campaign_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not camp.data:
        raise HTTPException(404, "Campanha nao encontrada")
    row = camp.data[0]
    plataforma = (row.get("ad_accounts") or {}).get("plataforma", "meta")
    svc = _get_service(plataforma)
    ok = await svc.update_campaign_status(row, body.action)
    if not ok:
        raise HTTPException(502, f"Falha ao comunicar com {plataforma}")
    return {"detail": f"Campanha {body.action} aplicado", "campaign_id": campaign_id, "plataforma": plataforma}


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
        .select("*, ad_accounts(plataforma)")
        .eq("id", campaign_id)
        .eq("workspace_id", current_user["workspace_id"])
        .limit(1)
        .execute()
    )
    if not camp.data:
        raise HTTPException(404, "Campanha nao encontrada")
    row = camp.data[0]
    plataforma = (row.get("ad_accounts") or {}).get("plataforma", "meta")
    svc = _get_service(plataforma)
    ok = await svc.update_campaign_budget(
        row,
        orcamento_diario_centavos=body.orcamento_diario_centavos,
        orcamento_total_centavos=body.orcamento_total_centavos,
    )
    if not ok:
        raise HTTPException(502, f"Falha ao comunicar com {plataforma}")
    return {"detail": "Orcamento atualizado", "plataforma": plataforma}


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
    plataforma: str = Query(None),
):
    """Agrega metricas por dia para graficos + totais."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    if not desde:
        desde = (date.today() - timedelta(days=30)).isoformat()
    if not ate:
        ate = date.today().isoformat()

    # Filtro por plataforma: buscar ad_account_ids da plataforma
    plataforma_account_ids: list[str] | None = None
    if plataforma:
        accs = (
            supabase.table("ad_accounts")
            .select("id")
            .eq("workspace_id", workspace_id)
            .eq("plataforma", plataforma)
            .execute()
            .data or []
        )
        plataforma_account_ids = [a["id"] for a in accs]
        if not plataforma_account_ids:
            return {
                "periodo": {"desde": desde, "ate": ate},
                "totais": {"impressoes": 0, "cliques": 0, "conversoes": 0,
                           "gasto_centavos": 0, "receita_centavos": 0,
                           "cpa_centavos": 0, "roas": 0.0, "ctr": 0.0},
                "serie": [],
            }

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
    if plataforma_account_ids:
        q = q.in_("ad_account_id", plataforma_account_ids)
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


@router.get("/metrics/cross-platform")
async def metrics_cross_platform(
    current_user: dict = Depends(get_current_user),
    desde: str = Query(None),
    ate: str = Query(None),
):
    """Compara metricas agregadas por plataforma (meta/google/tiktok)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    if not desde:
        desde = (date.today() - timedelta(days=30)).isoformat()
    if not ate:
        ate = date.today().isoformat()

    accounts = (
        supabase.table("ad_accounts")
        .select("id,plataforma")
        .eq("workspace_id", workspace_id)
        .execute()
        .data or []
    )
    plat_map: dict[str, str] = {a["id"]: a["plataforma"] for a in accounts}

    rows = (
        supabase.table("ad_metrics_daily")
        .select("*")
        .eq("workspace_id", workspace_id)
        .gte("data", desde)
        .lte("data", ate)
        .execute()
        .data or []
    )

    por_plataforma: dict[str, dict[str, float]] = {}
    for r in rows:
        plat = plat_map.get(r.get("ad_account_id"), "desconhecida")
        bucket = por_plataforma.setdefault(plat, {
            "plataforma": plat, "impressoes": 0, "cliques": 0,
            "conversoes": 0, "gasto_centavos": 0, "receita_centavos": 0,
        })
        for k in ("impressoes", "cliques", "conversoes", "gasto_centavos", "receita_centavos"):
            bucket[k] = (bucket.get(k) or 0) + (r.get(k) or 0)

    resultado = []
    for plat, v in por_plataforma.items():
        gasto = v["gasto_centavos"] or 0
        conv = v["conversoes"] or 0
        rec = v["receita_centavos"] or 0
        impr = v["impressoes"] or 0
        v["cpa_centavos"] = (gasto // conv) if conv else 0
        v["roas"] = round((rec / gasto), 4) if gasto else 0.0
        v["ctr"] = round((v["cliques"] / impr * 100), 2) if impr else 0.0
        resultado.append(v)

    resultado.sort(key=lambda x: x.get("gasto_centavos", 0), reverse=True)
    return {"periodo": {"desde": desde, "ate": ate}, "plataformas": resultado}


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
