"""
Benchmark — Pesquisa e monitoramento de concorrentes (Sessao 10).

Endpoints:
  GET    /benchmark/competitors
  POST   /benchmark/competitors
  PUT    /benchmark/competitors/{id}
  DELETE /benchmark/competitors/{id}
  POST   /benchmark/analyze                 — dispara analise (async via Celery)
  GET    /benchmark/reports                 — lista relatorios
  GET    /benchmark/reports/{id}            — detalhe completo (metricas + keywords)
  DELETE /benchmark/reports/{id}
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.db import get_supabase
from core.billing import get_workspace_subscription, get_workspace_usage
from modules.benchmark.schemas import (
    CompetitorCreate,
    CompetitorUpdate,
    BenchmarkAnalyzeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


def _ensure_benchmark_plan(workspace_id: str):
    """Free nao tem acesso; demais planos checam limite via usage."""
    sub = get_workspace_subscription(workspace_id)
    if not sub:
        raise HTTPException(403, "Assinatura nao encontrada")
    plan = sub.get("plans") or {}
    slug = (plan.get("slug") or "").lower()
    if slug == "free":
        raise HTTPException(
            403, "Benchmark indisponivel no plano Free. Faca upgrade."
        )
    max_bench = plan.get("max_benchmarks_mes")
    if max_bench is not None:
        usage = get_workspace_usage(workspace_id)
        atual = usage.get("benchmarks_executados", 0)
        if atual >= max_bench:
            raise HTTPException(
                429,
                f"Limite de benchmarks/mes atingido ({atual}/{max_bench}). "
                "Faca upgrade do plano.",
            )


# ============================================================
# Competitors
# ============================================================

def _ensure_negocio_pertence(workspace_id: str, negocio_id: str) -> None:
    """Valida que o negocio existe e pertence ao workspace atual."""
    supabase = get_supabase()
    res = (
        supabase.table("negocios")
        .select("id")
        .eq("id", negocio_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        raise HTTPException(404, "Negocio nao encontrado neste workspace")


@router.get("/competitors")
async def list_competitors(
    current_user: dict = Depends(get_current_user),
    negocio_id: str = Query(None, description="Filtrar por negocio"),
):
    supabase = get_supabase()
    q = (
        supabase.table("competitors")
        .select("*, negocios(nome)")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
    )
    if negocio_id:
        q = q.eq("negocio_id", negocio_id)
    return q.execute().data or []


@router.post("/competitors")
async def create_competitor(
    body: CompetitorCreate,
    current_user: dict = Depends(get_current_user),
):
    _ensure_negocio_pertence(current_user["workspace_id"], body.negocio_id)
    supabase = get_supabase()
    data = body.model_dump()
    data["workspace_id"] = current_user["workspace_id"]
    result = supabase.table("competitors").insert(data).execute()
    return result.data[0]


@router.put("/competitors/{competitor_id}")
async def update_competitor(
    competitor_id: str,
    body: CompetitorUpdate,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    update = body.model_dump(exclude_none=True)
    update["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("competitors")
        .update(update)
        .eq("id", competitor_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Concorrente nao encontrado")
    return result.data[0]


@router.delete("/competitors/{competitor_id}")
async def delete_competitor(
    competitor_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = (
        supabase.table("competitors")
        .delete()
        .eq("id", competitor_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Concorrente nao encontrado")
    return {"detail": "Concorrente removido"}


# ============================================================
# Analyze + Reports
# ============================================================

@router.post("/analyze")
async def analyze(
    body: BenchmarkAnalyzeRequest,
    current_user: dict = Depends(get_current_user),
):
    _ensure_benchmark_plan(current_user["workspace_id"])
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    _ensure_negocio_pertence(workspace_id, body.negocio_id)

    # Concorrentes devem pertencer ao mesmo negocio do relatorio
    comps = (
        supabase.table("competitors")
        .select("id")
        .in_("id", body.competitor_ids)
        .eq("workspace_id", workspace_id)
        .eq("negocio_id", body.negocio_id)
        .execute()
        .data or []
    )
    ids_validos = [c["id"] for c in comps]
    if not ids_validos:
        raise HTTPException(400, "Nenhum concorrente valido para este negocio")

    report = {
        "workspace_id": workspace_id,
        "negocio_id": body.negocio_id,
        "nome": body.nome,
        "competitor_ids": ids_validos,
        "parametros": {
            "redes": [r.value for r in body.redes],
            "incluir_keywords": body.incluir_keywords,
            "incluir_insights": body.incluir_insights,
            "contexto_negocio": body.contexto_negocio,
        },
        "status": "pendente",
        "criado_por": current_user["id"],
    }
    result = supabase.table("benchmark_reports").insert(report).execute()
    if not result.data:
        raise HTTPException(500, "Falha ao criar relatorio")
    report_id = result.data[0]["id"]

    # Disparar via Celery (com fallback sincrono se fila indisponivel)
    task_id = None
    try:
        from modules.benchmark.tasks import run_benchmark_analysis
        async_res = run_benchmark_analysis.delay(report_id)
        task_id = async_res.id
    except Exception as e:
        logger.warning(f"[benchmark] Celery indisponivel — rodando inline: {e}")
        try:
            from modules.benchmark.services.analyzer import run_analysis
            run_analysis(report_id)
        except Exception as e2:
            logger.exception(f"[benchmark] analise inline falhou: {e2}")

    return {"report_id": report_id, "task_id": task_id, "status": "pendente"}


@router.get("/reports")
async def list_reports(
    current_user: dict = Depends(get_current_user),
    negocio_id: str = Query(None, description="Filtrar por negocio"),
):
    supabase = get_supabase()
    q = (
        supabase.table("benchmark_reports")
        .select("id,negocio_id,nome,status,competitor_ids,parametros,resumo,criado_em,concluido_em,erro_msg,negocios(nome)")
        .eq("workspace_id", current_user["workspace_id"])
        .order("criado_em", desc=True)
        .limit(50)
    )
    if negocio_id:
        q = q.eq("negocio_id", negocio_id)
    return q.execute().data or []


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]
    rep = (
        supabase.table("benchmark_reports")
        .select("*")
        .eq("id", report_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    )
    if not rep.data:
        raise HTTPException(404, "Relatorio nao encontrado")
    report = rep.data[0]

    metricas = (
        supabase.table("benchmark_metrics")
        .select("*, competitors(nome, segmento)")
        .eq("report_id", report_id)
        .execute()
        .data or []
    )
    keywords = (
        supabase.table("benchmark_keywords")
        .select("*, competitors(nome)")
        .eq("report_id", report_id)
        .order("relevancia", desc=True)
        .execute()
        .data or []
    )
    competitors = (
        supabase.table("competitors")
        .select("id,nome,segmento,website,instagram_handle,youtube_handle,tiktok_handle")
        .in_("id", report.get("competitor_ids") or [])
        .execute()
        .data or []
    )
    return {
        **report,
        "competitors": competitors,
        "metricas": metricas,
        "keywords": keywords,
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = (
        supabase.table("benchmark_reports")
        .delete()
        .eq("id", report_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Relatorio nao encontrado")
    return {"detail": "Relatorio removido"}
