"""
Aggregator service para o Dashboard.
Queries otimizadas para KPIs, métricas de vídeo, uso do plano e timeline.
Usa cache Redis quando disponível.
"""

import json
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from core.config import get_settings
from core.db import get_supabase
from core.billing import get_workspace_subscription, get_workspace_usage

logger = logging.getLogger(__name__)
settings = get_settings()

# Cache TTL em segundos
CACHE_TTL = 60  # 1 minuto


def _get_redis():
    """Retorna cliente Redis se disponível, None caso contrário."""
    try:
        import redis
        return redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def _cache_get(key: str) -> Optional[dict]:
    """Busca valor do cache Redis."""
    r = _get_redis()
    if not r:
        return None
    try:
        val = r.get(key)
        if val:
            return json.loads(val)
    except Exception:
        pass
    return None


def _cache_set(key: str, value, ttl: int = CACHE_TTL):
    """Salva valor no cache Redis."""
    r = _get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def _get_workspace_negocio_ids(workspace_id: str) -> list[str]:
    """Retorna IDs de todos os negócios do workspace."""
    supabase = get_supabase()
    result = (
        supabase.table("negocios")
        .select("id")
        .eq("workspace_id", workspace_id)
        .execute()
    )
    return [n["id"] for n in (result.data or [])]


def get_overview(workspace_id: str) -> dict:
    """
    KPIs gerais do workspace:
    - Total de negócios ativos
    - Vídeos gerados/publicados no mês
    - Aprovações pendentes
    - Taxa de aprovação
    - Plano atual e status
    """
    cache_key = f"dashboard:overview:{workspace_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    supabase = get_supabase()

    # Total de negócios ativos
    negocios_result = (
        supabase.table("negocios")
        .select("id", count="exact")
        .eq("workspace_id", workspace_id)
        .eq("status", "ativo")
        .execute()
    )
    total_negocios = negocios_result.count or 0

    # IDs dos negócios do workspace (para filtrar vídeos)
    negocio_ids = _get_workspace_negocio_ids(workspace_id)

    total_videos_mes = 0
    publicados_mes = 0
    total_pendentes = 0
    taxa_aprovacao = 0.0

    if negocio_ids:
        # Vídeos do mês atual
        first_day = date.today().replace(day=1).isoformat()
        videos_mes = (
            supabase.table("videos")
            .select("id, status, publicado_em")
            .in_("negocio_id", negocio_ids)
            .gte("criado_em", first_day)
            .execute()
        )
        videos_mes_data = videos_mes.data or []
        total_videos_mes = len(videos_mes_data)
        publicados_mes = sum(
            1 for v in videos_mes_data if v.get("status") == "publicado"
        )

        # Aprovações pendentes
        pendentes = (
            supabase.table("videos")
            .select("id", count="exact")
            .in_("negocio_id", negocio_ids)
            .eq("status", "aguardando_aprovacao")
            .execute()
        )
        total_pendentes = pendentes.count or 0

        # Taxa de aprovação (últimos 30 dias)
        trinta_dias_atras = (date.today() - timedelta(days=30)).isoformat()
        videos_30d = (
            supabase.table("videos")
            .select("status")
            .in_("negocio_id", negocio_ids)
            .gte("criado_em", trinta_dias_atras)
            .in_("status", ["aprovado", "publicado", "rejeitado"])
            .execute()
        )
        aprovados_30d = sum(
            1 for v in (videos_30d.data or [])
            if v.get("status") in ("aprovado", "publicado")
        )
        total_decisoes = len(videos_30d.data or [])
        taxa_aprovacao = round(
            (aprovados_30d / total_decisoes * 100) if total_decisoes > 0 else 0, 1
        )

    # Subscription e plano
    sub = get_workspace_subscription(workspace_id)
    plano_nome = "Sem plano"
    plano_status = "inactive"
    if sub:
        plano_nome = sub.get("plans", {}).get("nome", "Sem plano") if sub.get("plans") else "Sem plano"
        plano_status = sub.get("status", "inactive")

    result = {
        "total_negocios": total_negocios,
        "videos_gerados_mes": total_videos_mes,
        "videos_publicados_mes": publicados_mes,
        "aprovacoes_pendentes": total_pendentes,
        "taxa_aprovacao_30d": taxa_aprovacao,
        "plano_nome": plano_nome,
        "plano_status": plano_status,
    }

    _cache_set(cache_key, result)
    return result


def get_video_engine_metrics(workspace_id: str) -> dict:
    """
    Métricas detalhadas do Video Engine:
    - Vídeos por status
    - Evolução diária (últimos 30 dias)
    - Top negócios por vídeos publicados
    """
    cache_key = f"dashboard:video_engine:{workspace_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    supabase = get_supabase()
    negocio_ids = _get_workspace_negocio_ids(workspace_id)

    if not negocio_ids:
        result = {
            "por_status": {},
            "evolucao_30d": [],
            "top_negocios": [],
            "total_30d": 0,
        }
        _cache_set(cache_key, result)
        return result

    trinta_dias_atras = (date.today() - timedelta(days=30)).isoformat()

    # Vídeos por status (últimos 30 dias)
    videos = (
        supabase.table("videos")
        .select("id, status, criado_em, publicado_em, negocio_id")
        .in_("negocio_id", negocio_ids)
        .gte("criado_em", trinta_dias_atras)
        .execute()
    )
    videos_data = videos.data or []

    status_counts = {}
    for v in videos_data:
        s = v.get("status", "desconhecido")
        status_counts[s] = status_counts.get(s, 0) + 1

    # Evolução diária (últimos 30 dias)
    evolucao = []
    for i in range(30):
        dia = date.today() - timedelta(days=29 - i)
        dia_str = dia.isoformat()
        gerados = sum(
            1 for v in videos_data
            if v.get("criado_em", "")[:10] == dia_str
        )
        publicados = sum(
            1 for v in videos_data
            if v.get("publicado_em") and v["publicado_em"][:10] == dia_str
        )
        evolucao.append({
            "data": dia_str,
            "gerados": gerados,
            "publicados": publicados,
        })

    # Top negócios por vídeos publicados
    negocio_pub_count = {}
    for v in videos_data:
        if v.get("status") == "publicado" and v.get("negocio_id"):
            nid = v["negocio_id"]
            negocio_pub_count[nid] = negocio_pub_count.get(nid, 0) + 1

    # Buscar nomes dos top negócios
    top_negocios = []
    if negocio_pub_count:
        top_ids = sorted(negocio_pub_count, key=negocio_pub_count.get, reverse=True)[:5]
        negocios_info = (
            supabase.table("negocios")
            .select("id, nome")
            .in_("id", top_ids)
            .execute()
        )
        nome_map = {n["id"]: n["nome"] for n in (negocios_info.data or [])}
        for nid in top_ids:
            top_negocios.append({
                "negocio_id": nid,
                "nome": nome_map.get(nid, nid[:8] + "..."),
                "publicados": negocio_pub_count[nid],
            })

    result = {
        "por_status": status_counts,
        "evolucao_30d": evolucao,
        "top_negocios": top_negocios,
        "total_30d": len(videos_data),
    }

    _cache_set(cache_key, result)
    return result


def get_usage_vs_limits(workspace_id: str) -> dict:
    """
    Consumo atual vs limites do plano:
    - Cada métrica com valor atual, limite máximo e percentual
    """
    cache_key = f"dashboard:usage:{workspace_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    usage = get_workspace_usage(workspace_id)
    sub = get_workspace_subscription(workspace_id)

    plan = sub.get("plans", {}) if sub else {}

    def _metric(current, max_val, label):
        if max_val is None or max_val == 0:
            return {"label": label, "atual": current, "limite": None, "percentual": 0}
        pct = round(current / max_val * 100, 1) if max_val > 0 else 0
        return {"label": label, "atual": current, "limite": max_val, "percentual": pct}

    metrics = [
        _metric(
            usage.get("videos_gerados", 0),
            plan.get("max_videos_mes"),
            "Videos gerados",
        ),
        _metric(
            usage.get("videos_publicados", 0),
            plan.get("max_videos_mes"),
            "Videos publicados",
        ),
        _metric(
            usage.get("conteudos_gerados", 0),
            plan.get("max_conteudos_mes"),
            "Conteudos gerados",
        ),
    ]

    # Negócios ativos vs limite
    supabase = get_supabase()
    negocios_count = (
        supabase.table("negocios")
        .select("id", count="exact")
        .eq("workspace_id", workspace_id)
        .eq("status", "ativo")
        .execute()
    )
    metrics.insert(0, _metric(
        negocios_count.count or 0,
        plan.get("max_negocios") or plan.get("max_apps"),
        "Negocios ativos",
    ))

    # Storage
    storage_gb = round(usage.get("storage_bytes", 0) / (1024 ** 3), 2)
    storage_limit = plan.get("storage_max_gb")
    metrics.append(_metric(storage_gb, storage_limit, "Storage (GB)"))

    plano_nome = plan.get("nome", "Sem plano")
    plano_status = sub.get("status", "inactive") if sub else "inactive"
    trial_ends_at = sub.get("trial_ends_at") if sub else None

    result = {
        "plano_nome": plano_nome,
        "plano_status": plano_status,
        "trial_ends_at": trial_ends_at,
        "metrics": metrics,
    }

    _cache_set(cache_key, result)
    return result


def get_timeline(workspace_id: str, limit: int = 20) -> list:
    """
    Atividade recente cross-módulo via audit_log.
    Retorna últimas N ações do workspace.
    """
    cache_key = f"dashboard:timeline:{workspace_id}:{limit}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    supabase = get_supabase()

    result = (
        supabase.table("audit_log")
        .select("id, acao, recurso, recurso_id, detalhes, user_id, criado_em")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .limit(limit)
        .execute()
    )

    entries = []
    for row in (result.data or []):
        acao = row.get("acao", "")
        descricao = _humanize_acao(acao, row.get("recurso"), row.get("detalhes"))
        entries.append({
            "id": row["id"],
            "acao": acao,
            "descricao": descricao,
            "recurso": row.get("recurso"),
            "recurso_id": row.get("recurso_id"),
            "user_id": row.get("user_id"),
            "criado_em": row.get("criado_em"),
        })

    _cache_set(cache_key, entries, ttl=30)  # cache curto para timeline
    return entries


def _humanize_acao(acao: str, recurso: Optional[str], detalhes: Optional[dict]) -> str:
    """Converte ação do audit_log em texto legível."""
    mapa = {
        "login": "Fez login na plataforma",
        "signup": "Criou uma conta",
        "forgot_password": "Solicitou recuperacao de senha",
        "reset_password": "Redefiniu a senha",
        "change_password": "Alterou a senha",
        "create_negocio": "Criou um novo negocio",
        "delete_negocio": "Removeu um negocio",
        "trigger_pipeline": "Disparou o pipeline de geracao",
        "publish_video": "Publicou um video",
        "approve_video": "Aprovou um video",
        "billing_checkout": "Iniciou checkout de plano",
        "billing_cancel": "Cancelou a assinatura",
        "invite_user": "Convidou um usuario",
        "remove_user": "Removeu um usuario",
        "export_data": "Exportou dados (LGPD)",
        "delete_data_request": "Solicitou exclusao de dados",
    }
    return mapa.get(acao, f"Acao: {acao}")
