"""
modules/benchmark/services/analyzer.py — Motor de analise de concorrentes.
Sessao 10.

Estrategia:
- Coleta publica leve (sem credenciais OAuth) via heuristicas por handle/URL.
  Quando uma API real nao esta configurada, producao populara as metricas
  com estimativas/placeholders derivados dos dados cadastrados.
- Analise de palavras-chave e insights usando Gemini (texto estruturado JSON).
- Salva metricas em benchmark_metrics e keywords em benchmark_keywords.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any

import google.generativeai as genai

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)
settings = get_settings()


# ------------------------------------------------------------
# Coleta de metricas por rede (placeholder + hook para APIs reais)
# ------------------------------------------------------------

def _metrics_stub(competitor: dict, rede: str) -> dict:
    """Gera linha de metricas baseada no que se tem cadastrado.

    Em producao, plugar chamadas reais (Instagram Graph, YouTube Data API,
    TikTok Display API) substituindo este stub. Aqui devolvemos None quando
    nao ha handle para a rede.
    """
    handle_field = {
        "instagram": "instagram_handle",
        "youtube": "youtube_handle",
        "tiktok": "tiktok_handle",
    }.get(rede)

    if rede == "website":
        if not competitor.get("website"):
            return None
        return {
            "rede": "website",
            "seguidores": None,
            "publicacoes": None,
            "engajamento_medio": None,
            "dados_extras": {"url": competitor.get("website")},
        }

    if not handle_field or not competitor.get(handle_field):
        return None

    return {
        "rede": rede,
        "seguidores": None,
        "seguindo": None,
        "publicacoes": None,
        "engajamento_medio": None,
        "visualizacoes_medias": None,
        "curtidas_medias": None,
        "comentarios_medios": None,
        "frequencia_semanal": None,
        "dados_extras": {"handle": competitor.get(handle_field)},
    }


# ------------------------------------------------------------
# Gemini: palavras-chave e insights
# ------------------------------------------------------------

def _configure_gemini() -> Any | None:
    if not settings.gemini_api_key:
        logger.warning("[benchmark] GEMINI_API_KEY nao configurado — pulando analise IA")
        return None
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


def _extract_json(texto: str) -> Any:
    """Extrai JSON de uma resposta que pode vir com fences markdown."""
    if not texto:
        return None
    t = texto.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lower().startswith("json"):
            t = t[4:]
    t = t.strip()
    inicio = t.find("{")
    if inicio == -1:
        inicio = t.find("[")
    if inicio == -1:
        return None
    try:
        return json.loads(t[inicio:])
    except Exception:
        return None


def analisar_keywords_com_ia(competitors: list[dict], contexto: str | None) -> list[dict]:
    """Solicita ao Gemini palavras-chave relevantes para o conjunto de concorrentes."""
    model = _configure_gemini()
    if model is None:
        return []

    resumo = "\n".join([
        f"- {c.get('nome')} ({c.get('segmento') or 'segmento nao informado'}) — "
        f"site: {c.get('website') or '—'} | ig: @{c.get('instagram_handle') or '—'} | "
        f"yt: {c.get('youtube_handle') or '—'} | tt: @{c.get('tiktok_handle') or '—'}"
        for c in competitors
    ])

    prompt = f"""Voce e um analista de marketing digital.

Analise os concorrentes abaixo e identifique as 10 palavras-chave mais estrategicas
(mistura de short-tail e long-tail) que eles provavelmente disputam.

=== CONTEXTO DE NEGOCIO ===
{contexto or 'Nao informado'}

=== CONCORRENTES ===
{resumo}

Retorne APENAS um JSON valido com a estrutura:
{{
  "keywords": [
    {{
      "palavra": "string",
      "relevancia": 0.0-1.0,
      "intencao": "informacional|comercial|transacional|navegacional",
      "volume_estimado": inteiro (busca mensal estimada no Brasil),
      "competitor_associado": "nome do concorrente mais associado ou null"
    }}
  ]
}}
"""
    try:
        resp = model.generate_content(prompt)
        data = _extract_json(resp.text or "")
        if not data or "keywords" not in data:
            return []
        return data["keywords"][:20]
    except Exception as e:
        logger.exception(f"[benchmark] Gemini keywords falhou: {e}")
        return []


def gerar_insights_com_ia(
    competitors: list[dict],
    metrics_rows: list[dict],
    keywords: list[dict],
    contexto: str | None,
) -> dict:
    """Gera resumo textual + lista de insights acionaveis."""
    model = _configure_gemini()
    if model is None:
        return {
            "resumo": "Analise IA indisponivel (GEMINI_API_KEY nao configurado).",
            "insights": [],
        }

    prompt = f"""Voce e um consultor estrategico de marketing digital.

Com base nos dados abaixo, escreva um RESUMO executivo (ate 5 linhas) e liste
de 5 a 8 INSIGHTS acionaveis, classificados por impacto (alto/medio/baixo).

=== CONTEXTO ===
{contexto or 'Nao informado'}

=== CONCORRENTES ===
{json.dumps([{k: c.get(k) for k in ('nome','segmento','website','descricao')} for c in competitors], ensure_ascii=False)}

=== METRICAS COLETADAS ===
{json.dumps(metrics_rows, ensure_ascii=False, default=str)}

=== KEYWORDS ===
{json.dumps(keywords, ensure_ascii=False)}

Retorne APENAS um JSON valido com a estrutura:
{{
  "resumo": "string curta",
  "insights": [
    {{
      "titulo": "string",
      "descricao": "string",
      "impacto": "alto|medio|baixo",
      "categoria": "posicionamento|conteudo|canal|preco|oportunidade"
    }}
  ]
}}
"""
    try:
        resp = model.generate_content(prompt)
        data = _extract_json(resp.text or "")
        if not data:
            return {"resumo": "Falha ao interpretar resposta da IA.", "insights": []}
        return {
            "resumo": data.get("resumo") or "",
            "insights": data.get("insights") or [],
        }
    except Exception as e:
        logger.exception(f"[benchmark] Gemini insights falhou: {e}")
        return {"resumo": f"Erro na IA: {e}", "insights": []}


# ------------------------------------------------------------
# Orquestracao principal
# ------------------------------------------------------------

def run_analysis(report_id: str) -> dict:
    """Executa a analise completa de um relatorio.

    Fluxo:
      1. Marca status=processando.
      2. Carrega competitors e parametros do relatorio.
      3. Coleta metricas por rede (stub hoje).
      4. Analisa keywords via Gemini.
      5. Gera insights via Gemini.
      6. Persiste metricas e keywords, atualiza relatorio com resumo+insights.
    """
    supabase = get_supabase()

    rep_res = supabase.table("benchmark_reports").select("*").eq("id", report_id).limit(1).execute()
    if not rep_res.data:
        logger.error(f"[benchmark] Relatorio {report_id} nao encontrado")
        return {"status": "erro", "erro": "relatorio nao encontrado"}

    report = rep_res.data[0]
    workspace_id = report["workspace_id"]
    params = report.get("parametros") or {}
    redes = params.get("redes") or ["instagram", "youtube", "tiktok"]
    competitor_ids = report.get("competitor_ids") or []
    contexto = params.get("contexto_negocio")

    supabase.table("benchmark_reports").update({
        "status": "processando",
        "iniciado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", report_id).execute()

    try:
        comp_res = (
            supabase.table("competitors")
            .select("*")
            .in_("id", competitor_ids)
            .eq("workspace_id", workspace_id)
            .execute()
        )
        competitors = comp_res.data or []
        if not competitors:
            raise ValueError("Nenhum concorrente valido encontrado")

        # 3. Metricas
        metrics_rows: list[dict] = []
        for c in competitors:
            for rede in redes:
                m = _metrics_stub(c, rede)
                if m is None:
                    continue
                row = {
                    "workspace_id": workspace_id,
                    "report_id": report_id,
                    "competitor_id": c["id"],
                    **m,
                }
                metrics_rows.append(row)
        if metrics_rows:
            supabase.table("benchmark_metrics").insert(metrics_rows).execute()

        # 4. Keywords
        keywords: list[dict] = []
        if params.get("incluir_keywords", True):
            kws = analisar_keywords_com_ia(competitors, contexto)
            if kws:
                comp_by_name = {c["nome"].lower(): c["id"] for c in competitors}
                for k in kws:
                    assoc = (k.get("competitor_associado") or "").lower()
                    comp_id = comp_by_name.get(assoc)
                    keywords.append({
                        "workspace_id": workspace_id,
                        "report_id": report_id,
                        "competitor_id": comp_id,
                        "palavra": str(k.get("palavra", ""))[:255],
                        "relevancia": float(k.get("relevancia") or 0),
                        "intencao": k.get("intencao"),
                        "volume_estimado": int(k.get("volume_estimado") or 0) or None,
                    })
                if keywords:
                    supabase.table("benchmark_keywords").insert(keywords).execute()

        # 5. Insights
        insights_payload = {"resumo": "", "insights": []}
        if params.get("incluir_insights", True):
            insights_payload = gerar_insights_com_ia(
                competitors, metrics_rows, keywords, contexto
            )

        supabase.table("benchmark_reports").update({
            "status": "concluido",
            "resumo": insights_payload.get("resumo"),
            "insights": insights_payload.get("insights"),
            "concluido_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()

        # incrementar contador de uso
        try:
            from core.billing import increment_usage
            increment_usage(workspace_id, "benchmarks_executados", 1)
        except Exception as e:
            logger.warning(f"[benchmark] falha ao incrementar usage: {e}")

        return {
            "status": "concluido",
            "report_id": report_id,
            "metricas": len(metrics_rows),
            "keywords": len(keywords),
            "insights": len(insights_payload.get("insights") or []),
        }

    except Exception as exc:
        logger.exception(f"[benchmark] analise falhou: {exc}")
        supabase.table("benchmark_reports").update({
            "status": "erro",
            "erro_msg": str(exc),
            "concluido_em": datetime.now(timezone.utc).isoformat(),
        }).eq("id", report_id).execute()
        return {"status": "erro", "erro": str(exc)}
