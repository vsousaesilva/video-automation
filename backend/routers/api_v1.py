"""
API publica v1 (Sessao 12).

Autenticada via header `X-API-Key: uks_live_...`.
Disponivel apenas para workspaces com plano `api_publica=true` (Enterprise).

Endpoints read-only nesta primeira versao — suficiente para dashboards de
terceiros. Mutacoes (criar conteudo, disparar pipeline) ficam para v2 apos
validacao com clientes reais.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from core.db import get_supabase

router = APIRouter(prefix="/api/v1", tags=["public-api"])


# ============================================================
# Auth por API Key
# ============================================================

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Retorna (raw_key, prefix, hash). raw_key so eh exibida uma vez."""
    raw = f"uks_live_{secrets.token_urlsafe(32)}"
    return raw, raw[:12], _hash_key(raw)


async def require_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> dict:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="missing_api_key")

    supabase = get_supabase()
    key_hash = _hash_key(x_api_key)

    result = (
        supabase.table("api_keys")
        .select("*, workspaces(id, nome), plans:workspaces(subscriptions(plans(api_publica)))")
        .eq("key_hash", key_hash)
        .eq("ativo", True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise HTTPException(status_code=401, detail="invalid_api_key")

    key = rows[0]

    if key.get("expira_em"):
        try:
            exp = datetime.fromisoformat(key["expira_em"].replace("Z", "+00:00"))
            if exp < datetime.now(timezone.utc):
                raise HTTPException(status_code=401, detail="expired_api_key")
        except (ValueError, AttributeError):
            pass

    # Verifica se o plano atual do workspace permite API publica
    sub_res = (
        supabase.table("subscriptions")
        .select("status, plans(api_publica)")
        .eq("workspace_id", key["workspace_id"])
        .eq("status", "active")
        .limit(1)
        .execute()
    )
    sub = (sub_res.data or [None])[0]
    if not sub or not (sub.get("plans") or {}).get("api_publica"):
        raise HTTPException(
            status_code=403,
            detail="api_publica_nao_disponivel_no_plano",
        )

    # Atualiza ultimo_uso_em (fire-and-forget)
    try:
        supabase.table("api_keys").update(
            {"ultimo_uso_em": datetime.now(timezone.utc).isoformat()}
        ).eq("id", key["id"]).execute()
    except Exception:
        pass

    return key


# ============================================================
# Schemas de admin (criacao/revogacao de keys via painel web)
# ============================================================

class ApiKeyCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=lambda: ["read"])
    expira_em: Optional[datetime] = None


class ApiKeyCreateResponse(BaseModel):
    id: str
    prefix: str
    raw_key: str  # exibida uma unica vez
    nome: str
    scopes: list[str]
    criado_em: datetime


class ApiKeyListItem(BaseModel):
    id: str
    prefix: str
    nome: str
    scopes: list[str]
    ativo: bool
    ultimo_uso_em: Optional[datetime]
    criado_em: datetime
    expira_em: Optional[datetime]


# ============================================================
# Endpoints administrativos (dentro da plataforma — JWT)
# ============================================================

from core.auth import get_current_user
from core.billing import get_workspace_subscription

admin_router = APIRouter(prefix="/api-keys", tags=["api-keys-admin"])


def _ensure_enterprise(workspace_id: str):
    sub = get_workspace_subscription(workspace_id)
    if not sub or not sub.get("plans"):
        raise HTTPException(status_code=403, detail="sem_subscription_ativa")
    if not sub["plans"].get("api_publica"):
        raise HTTPException(status_code=403, detail="upgrade_para_enterprise_para_usar_api")


@admin_router.get("", response_model=list[ApiKeyListItem])
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    workspace_id = current_user["workspace_id"]
    _ensure_enterprise(workspace_id)
    supabase = get_supabase()
    result = (
        supabase.table("api_keys")
        .select("id, prefix, nome, scopes, ativo, ultimo_uso_em, criado_em, expira_em")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .execute()
    )
    return result.data or []


@admin_router.post("", response_model=ApiKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: dict = Depends(get_current_user),
):
    workspace_id = current_user["workspace_id"]
    _ensure_enterprise(workspace_id)

    invalid = [s for s in payload.scopes if s not in ("read", "write")]
    if invalid:
        raise HTTPException(status_code=400, detail=f"scopes_invalidos: {invalid}")

    raw, prefix, key_hash = generate_api_key()
    supabase = get_supabase()
    ins = (
        supabase.table("api_keys")
        .insert({
            "workspace_id": workspace_id,
            "nome": payload.nome,
            "prefix": prefix,
            "key_hash": key_hash,
            "scopes": payload.scopes,
            "criado_por": current_user["id"],
            "expira_em": payload.expira_em.isoformat() if payload.expira_em else None,
        })
        .execute()
    )
    row = (ins.data or [None])[0]
    if not row:
        raise HTTPException(status_code=500, detail="falha_ao_criar_api_key")

    return ApiKeyCreateResponse(
        id=row["id"],
        prefix=prefix,
        raw_key=raw,
        nome=row["nome"],
        scopes=row["scopes"],
        criado_em=row["criado_em"],
    )


@admin_router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    current_user: dict = Depends(get_current_user),
):
    workspace_id = current_user["workspace_id"]
    supabase = get_supabase()
    supabase.table("api_keys").update({"ativo": False}).eq("id", key_id).eq(
        "workspace_id", workspace_id
    ).execute()
    return None


# ============================================================
# Endpoints publicos (autenticados via X-API-Key)
# ============================================================

@router.get("/me")
async def me(api_key: dict = Depends(require_api_key)) -> dict:
    return {
        "workspace_id": api_key["workspace_id"],
        "key_prefix": api_key["prefix"],
        "scopes": api_key["scopes"],
    }


@router.get("/negocios")
async def list_negocios(
    api_key: dict = Depends(require_api_key),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    supabase = get_supabase()
    result = (
        supabase.table("negocios")
        .select("id, nome, status, criado_em")
        .eq("workspace_id", api_key["workspace_id"])
        .order("criado_em", desc=True)
        .limit(limit)
        .execute()
    )
    return {"data": result.data or []}


@router.get("/videos")
async def list_videos(
    api_key: dict = Depends(require_api_key),
    negocio_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    supabase = get_supabase()
    q = (
        supabase.table("videos")
        .select("id, negocio_id, conteudo_id, status, url_vertical, url_horizontal, criado_em")
        .order("criado_em", desc=True)
        .limit(limit)
    )
    # Filtra por workspace via join
    q = q.in_(
        "negocio_id",
        [
            n["id"]
            for n in (
                supabase.table("negocios")
                .select("id")
                .eq("workspace_id", api_key["workspace_id"])
                .execute()
                .data
                or []
            )
        ],
    )
    if negocio_id:
        q = q.eq("negocio_id", negocio_id)
    result = q.execute()
    return {"data": result.data or []}


@router.get("/metrics/usage")
async def usage_metrics(api_key: dict = Depends(require_api_key)) -> dict:
    """Uso do mes corrente + limites do plano."""
    from core.billing import get_workspace_subscription, get_workspace_usage
    sub = get_workspace_subscription(api_key["workspace_id"])
    usage = get_workspace_usage(api_key["workspace_id"])
    plan = (sub or {}).get("plans") or {}
    return {
        "plan": plan.get("slug"),
        "usage": usage,
        "limits": {
            "videos_mes": plan.get("max_videos_mes"),
            "conteudos_mes": plan.get("max_conteudos_mes"),
            "negocios": plan.get("max_negocios"),
            "benchmarks_mes": plan.get("max_benchmarks_mes"),
            "contatos_crm": plan.get("max_contatos_crm"),
        },
    }
