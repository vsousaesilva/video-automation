"""
Endpoints LGPD: exportação e exclusão de dados do workspace.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from core.auth import get_current_user, require_role
from core.db import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/privacy", tags=["Privacidade / LGPD"])


@router.get("/my-data")
async def export_my_data(current_user: dict = Depends(get_current_user)):
    """Exporta todos os dados do workspace em JSON (LGPD Art. 18)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Coletar dados de todas as tabelas relacionadas ao workspace
    workspace = supabase.table("workspaces").select("*").eq("id", workspace_id).execute()
    users = supabase.table("users").select(
        "id, nome, email, papel, ativo, criado_em"
    ).eq("workspace_id", workspace_id).execute()
    negocios = supabase.table("negocios").select("*").eq("workspace_id", workspace_id).execute()
    conteudos = supabase.table("conteudos").select("*").eq("workspace_id", workspace_id).execute()
    videos = supabase.table("videos").select("*").eq("workspace_id", workspace_id).execute()
    subscriptions = supabase.table("subscriptions").select("*").eq("workspace_id", workspace_id).execute()
    invoices = supabase.table("invoices").select("*").eq("workspace_id", workspace_id).execute()
    usage = supabase.table("usage_metrics").select("*").eq("workspace_id", workspace_id).execute()
    audit = (
        supabase.table("audit_log")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .limit(500)
        .execute()
    )
    execution_logs = (
        supabase.table("execution_logs")
        .select("*")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .limit(500)
        .execute()
    )

    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "workspace": workspace.data[0] if workspace.data else None,
        "users": users.data,
        "negocios": negocios.data,
        "conteudos": conteudos.data,
        "videos": videos.data,
        "subscriptions": subscriptions.data,
        "invoices": invoices.data,
        "usage_metrics": usage.data,
        "audit_log": audit.data,
        "execution_logs": execution_logs.data,
    }


@router.delete("/my-data")
async def request_data_deletion(
    current_user: dict = Depends(require_role(["admin"])),
):
    """Solicita exclusão de dados do workspace (LGPD Art. 18).
    Agenda a exclusão para 30 dias (período de carência para cancelamento).
    """
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    now = datetime.now(timezone.utc)
    scheduled_for = now + timedelta(days=30)

    supabase.table("workspaces").update({
        "deletion_requested_at": now.isoformat(),
        "deletion_scheduled_for": scheduled_for.isoformat(),
    }).eq("id", workspace_id).execute()

    # Registrar no audit log
    supabase.table("audit_log").insert({
        "workspace_id": workspace_id,
        "user_id": current_user["id"],
        "acao": "delete_data_request",
        "recurso": "workspace",
        "recurso_id": workspace_id,
        "detalhes": {"scheduled_for": scheduled_for.isoformat()},
    }).execute()

    return {
        "detail": "Solicitação de exclusão registrada.",
        "scheduled_for": scheduled_for.isoformat(),
        "message": "Seus dados serão excluídos em 30 dias. Cancele a solicitação fazendo login antes desta data.",
    }


@router.post("/cancel-deletion")
async def cancel_data_deletion(
    current_user: dict = Depends(require_role(["admin"])),
):
    """Cancela uma solicitação de exclusão de dados."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    ws = supabase.table("workspaces").select("deletion_requested_at").eq("id", workspace_id).execute()
    if not ws.data or not ws.data[0].get("deletion_requested_at"):
        raise HTTPException(status_code=400, detail="Não há solicitação de exclusão pendente.")

    supabase.table("workspaces").update({
        "deletion_requested_at": None,
        "deletion_scheduled_for": None,
    }).eq("id", workspace_id).execute()

    return {"detail": "Solicitação de exclusão cancelada."}
