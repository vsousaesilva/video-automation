from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.db import get_supabase
from modules.video_engine.schemas import ConteudoResponse

router = APIRouter(prefix="/conteudos", tags=["Conteúdos"])


@router.get("", response_model=list[ConteudoResponse])
async def list_conteudos(
    negocio_id: Optional[str] = Query(None, description="Filtrar por negócio"),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    """Lista conteúdos gerados do workspace, com filtros opcionais."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Se app_id informado, validar que pertence ao workspace
    if negocio_id:
        neg_check = (
            supabase.table("negocios")
            .select("id")
            .eq("id", negocio_id)
            .eq("workspace_id", workspace_id)
            .execute()
        )
        if not neg_check.data:
            raise HTTPException(status_code=404, detail="Negócio não encontrado")

        query = (
            supabase.table("conteudos")
            .select("*")
            .eq("negocio_id", negocio_id)
        )
    else:
        negocios_result = (
            supabase.table("negocios")
            .select("id")
            .eq("workspace_id", workspace_id)
            .execute()
        )
        neg_ids = [n["id"] for n in negocios_result.data]
        if not neg_ids:
            return []

        query = (
            supabase.table("conteudos")
            .select("*")
            .in_("negocio_id", neg_ids)
        )

    if status:
        query = query.eq("status", status)

    result = query.order("criado_em", desc=True).limit(limit).execute()
    return result.data


@router.get("/{conteudo_id}", response_model=ConteudoResponse)
async def get_conteudo(
    conteudo_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Detalhes de um conteúdo específico."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    result = (
        supabase.table("conteudos")
        .select("*, negocios(workspace_id)")
        .eq("id", conteudo_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    conteudo = result.data[0]

    # Validar que o conteúdo pertence ao workspace do usuário
    app_info = conteudo.pop("negocios", None)
    if not app_info or app_info.get("workspace_id") != workspace_id:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    return conteudo
