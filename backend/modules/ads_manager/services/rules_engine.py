"""
Executa regras de automacao de ads configuradas pelos usuarios.

Formato da condicao (JSONB):
    {"metrica": "cpa", "operador": ">", "valor": 5000, "periodo_dias": 3}

Acoes suportadas: pause, activate, adjust_budget, notify.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from core.db import get_supabase

logger = logging.getLogger(__name__)

METRICAS_VALIDAS = {"cpa", "roas", "ctr", "gasto", "cliques", "impressoes", "conversoes"}
OPERADORES = {">": lambda a, b: a > b, "<": lambda a, b: a < b,
              ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b,
              "==": lambda a, b: a == b}


def _aggregate_metric(rows: list[dict[str, Any]], metrica: str) -> float:
    if not rows:
        return 0.0
    if metrica == "cpa":
        gasto = sum(r.get("gasto_centavos", 0) or 0 for r in rows)
        conv = sum(r.get("conversoes", 0) or 0 for r in rows)
        return (gasto / conv) if conv else 0.0
    if metrica == "roas":
        gasto = sum(r.get("gasto_centavos", 0) or 0 for r in rows)
        receita = sum(r.get("receita_centavos", 0) or 0 for r in rows)
        return (receita / gasto) if gasto else 0.0
    if metrica == "ctr":
        return sum(float(r.get("ctr", 0) or 0) for r in rows) / len(rows)
    mapping = {"gasto": "gasto_centavos", "cliques": "cliques",
               "impressoes": "impressoes", "conversoes": "conversoes"}
    col = mapping.get(metrica)
    if not col:
        return 0.0
    return float(sum(r.get(col, 0) or 0 for r in rows))


async def execute_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Avalia e executa uma regra. Retorna resumo."""
    from modules.ads_manager.services.meta_ads import (
        update_campaign_status,
        update_campaign_budget,
    )

    supabase = get_supabase()
    condicao = rule.get("condicao") or {}
    metrica = condicao.get("metrica")
    operador = condicao.get("operador")
    valor = condicao.get("valor")
    periodo = int(condicao.get("periodo_dias", 1))

    if metrica not in METRICAS_VALIDAS or operador not in OPERADORES:
        return {"executada": False, "motivo": "condicao_invalida"}

    since = (date.today() - timedelta(days=periodo)).isoformat()

    # Determinar escopo e campanhas alvo
    escopo = rule.get("escopo")
    escopo_ids = rule.get("escopo_ids") or []
    workspace_id = rule["workspace_id"]

    q = (
        supabase.table("campaigns")
        .select("*")
        .eq("workspace_id", workspace_id)
    )
    if rule.get("ad_account_id"):
        q = q.eq("ad_account_id", rule["ad_account_id"])
    if escopo == "campaign" and escopo_ids:
        q = q.in_("id", escopo_ids)
    campaigns = (q.execute().data or [])

    acoes_aplicadas: list[dict[str, Any]] = []

    for camp in campaigns:
        metrics = (
            supabase.table("ad_metrics_daily")
            .select("*")
            .eq("campaign_id", camp["id"])
            .gte("data", since)
            .execute()
            .data or []
        )
        valor_atual = _aggregate_metric(metrics, metrica)
        if not OPERADORES[operador](valor_atual, float(valor)):
            continue

        acao = rule.get("acao")
        params = rule.get("acao_params") or {}
        sucesso = False
        if acao == "pause":
            sucesso = await update_campaign_status(camp, "pause")
        elif acao == "activate":
            sucesso = await update_campaign_status(camp, "activate")
        elif acao == "adjust_budget":
            ajuste_pct = float(params.get("ajuste_pct", 0))
            atual = camp.get("orcamento_diario_centavos") or 0
            novo = int(atual * (1 + ajuste_pct / 100))
            sucesso = await update_campaign_budget(camp, orcamento_diario_centavos=novo)
        elif acao == "notify":
            sucesso = True  # notificacao e registrada abaixo

        acoes_aplicadas.append({
            "campaign_id": camp["id"],
            "campaign_nome": camp.get("nome"),
            "valor_atual": valor_atual,
            "acao": acao,
            "sucesso": sucesso,
        })

    supabase.table("ad_rules").update({
        "ultima_execucao": datetime.now(timezone.utc).isoformat(),
        "ultima_acao": {"acoes": acoes_aplicadas, "total": len(acoes_aplicadas)},
    }).eq("id", rule["id"]).execute()

    return {"executada": True, "acoes": acoes_aplicadas}


async def run_all_active_rules(workspace_id: str | None = None) -> dict[str, Any]:
    """Executa todas as regras ativas (ou de um workspace)."""
    supabase = get_supabase()
    q = supabase.table("ad_rules").select("*").eq("ativa", True)
    if workspace_id:
        q = q.eq("workspace_id", workspace_id)
    rules = q.execute().data or []

    resultados = []
    for r in rules:
        try:
            resultados.append({"rule_id": r["id"], "resultado": await execute_rule(r)})
        except Exception as e:
            logger.exception(f"[rules_engine] falha na regra {r['id']}: {e}")
            resultados.append({"rule_id": r["id"], "erro": str(e)})
    return {"total": len(rules), "resultados": resultados}
