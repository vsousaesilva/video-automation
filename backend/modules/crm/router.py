"""
CRM — Gestao de contatos, deals, funil e atividades.
GET    /crm/contacts            — listar contatos (busca, filtros, tags)
POST   /crm/contacts            — criar contato
GET    /crm/contacts/{id}       — detalhes do contato + atividades
PUT    /crm/contacts/{id}       — atualizar contato
DELETE /crm/contacts/{id}       — desativar contato (soft-delete)
POST   /crm/contacts/import     — importar contatos via CSV
GET    /crm/tags                — listar tags
POST   /crm/tags                — criar tag
PUT    /crm/tags/{id}           — atualizar tag
DELETE /crm/tags/{id}           — remover tag
GET    /crm/stages              — listar etapas do funil
POST   /crm/stages              — criar etapa
PUT    /crm/stages/{id}         — atualizar etapa
DELETE /crm/stages/{id}         — desativar etapa
GET    /crm/deals               — listar deals (kanban)
POST   /crm/deals               — criar deal
PUT    /crm/deals/{id}          — atualizar deal
PUT    /crm/deals/{id}/move     — mover deal entre etapas (kanban)
DELETE /crm/deals/{id}          — remover deal
GET    /crm/activities          — listar atividades
POST   /crm/activities          — criar atividade
PUT    /crm/activities/{id}     — atualizar atividade
DELETE /crm/activities/{id}     — remover atividade
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File

from core.auth import get_current_user
from core.db import get_supabase
from modules.crm.schemas import (
    ContactCreate,
    ContactUpdate,
    TagCreate,
    TagUpdate,
    StageCreate,
    StageUpdate,
    DealCreate,
    DealUpdate,
    DealMoveRequest,
    ActivityCreate,
    ActivityUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crm", tags=["CRM"])


# ============================================================
# Contatos
# ============================================================

@router.get("/contacts")
async def list_contacts(
    current_user: dict = Depends(get_current_user),
    search: str = Query(None, max_length=255),
    tag_id: str = Query(None),
    origem: str = Query(None),
    ativo: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    """Lista contatos com busca, filtros e paginacao."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("contacts")
        .select("*, contacts_tags(tag_id, contact_tags(id, nome, cor))", count="exact")
        .eq("workspace_id", workspace_id)
        .eq("ativo", ativo)
        .order("criado_em", desc=True)
    )

    if search:
        query = query.or_(f"nome.ilike.%{search}%,email.ilike.%{search}%,empresa.ilike.%{search}%,telefone.ilike.%{search}%")

    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    result = query.execute()
    contacts = result.data or []

    # Filtrar por tag no Python (Supabase nao suporta filtro em relacao facilmente)
    if tag_id:
        contacts = [
            c for c in contacts
            if any(t["tag_id"] == tag_id for t in (c.get("contacts_tags") or []))
        ]

    # Filtrar por origem
    if origem:
        contacts = [c for c in contacts if c.get("origem") == origem]

    # Formatar tags para resposta limpa
    for c in contacts:
        c["tags"] = [
            t["contact_tags"] for t in (c.get("contacts_tags") or [])
            if t.get("contact_tags")
        ]
        del c["contacts_tags"]

    return {
        "data": contacts,
        "total": result.count or 0,
        "page": page,
        "per_page": per_page,
    }


@router.post("/contacts/import")
async def import_contacts(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Importa contatos via CSV."""
    if not file.filename.endswith((".csv", ".xlsx", ".xls")):
        raise HTTPException(400, "Formato nao suportado. Use CSV ou Excel.")

    from modules.crm.services.importer import import_contacts_from_file

    content = await file.read()
    result = await import_contacts_from_file(
        content=content,
        filename=file.filename,
        workspace_id=current_user["workspace_id"],
    )
    return result


@router.post("/contacts")
async def create_contact(
    body: ContactCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria um novo contato."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    data = {
        "workspace_id": workspace_id,
        "nome": body.nome,
        "email": body.email,
        "telefone": body.telefone,
        "empresa": body.empresa,
        "cargo": body.cargo,
        "origem": body.origem.value if body.origem else "manual",
        "notas": body.notas,
        "dados_extras": body.dados_extras or {},
    }

    result = supabase.table("contacts").insert(data).execute()
    contact = result.data[0]

    # Associar tags
    if body.tag_ids:
        tag_rows = [{"contact_id": contact["id"], "tag_id": tid} for tid in body.tag_ids]
        supabase.table("contacts_tags").insert(tag_rows).execute()

    # Incrementar contatos_crm no billing
    try:
        from core.billing import increment_usage
        increment_usage(workspace_id, "contatos_crm")
    except Exception as e:
        logger.warning(f"Falha ao incrementar uso de contatos_crm: {e}")

    return contact


@router.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Detalhes do contato com tags e atividades recentes."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Contato
    result = (
        supabase.table("contacts")
        .select("*, contacts_tags(tag_id, contact_tags(id, nome, cor))")
        .eq("id", contact_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Contato nao encontrado")

    contact = result.data[0]
    contact["tags"] = [
        t["contact_tags"] for t in (contact.get("contacts_tags") or [])
        if t.get("contact_tags")
    ]
    del contact["contacts_tags"]

    # Atividades do contato
    activities_result = (
        supabase.table("activities")
        .select("*")
        .eq("contact_id", contact_id)
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .limit(50)
        .execute()
    )

    # Deals do contato
    deals_result = (
        supabase.table("deals")
        .select("*, deal_stages(id, nome, cor)")
        .eq("contact_id", contact_id)
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .limit(20)
        .execute()
    )

    return {
        "contact": contact,
        "activities": activities_result.data or [],
        "deals": deals_result.data or [],
    }


@router.put("/contacts/{contact_id}")
async def update_contact(
    contact_id: str,
    body: ContactUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza um contato."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Verificar que pertence ao workspace
    existing = (
        supabase.table("contacts")
        .select("id")
        .eq("id", contact_id)
        .eq("workspace_id", workspace_id)
        .limit(1)
        .execute()
    )
    if not existing.data:
        raise HTTPException(404, "Contato nao encontrado")

    update_data = body.model_dump(exclude_none=True, exclude={"tag_ids"})
    if body.origem:
        update_data["origem"] = body.origem.value
    update_data["atualizado_em"] = datetime.now(timezone.utc).isoformat()

    result = supabase.table("contacts").update(update_data).eq("id", contact_id).execute()

    # Atualizar tags se fornecidas
    if body.tag_ids is not None:
        supabase.table("contacts_tags").delete().eq("contact_id", contact_id).execute()
        if body.tag_ids:
            tag_rows = [{"contact_id": contact_id, "tag_id": tid} for tid in body.tag_ids]
            supabase.table("contacts_tags").insert(tag_rows).execute()

    return result.data[0] if result.data else {"id": contact_id, "updated": True}


@router.delete("/contacts/{contact_id}")
async def delete_contact(
    contact_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Desativa um contato (soft-delete)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    result = (
        supabase.table("contacts")
        .update({"ativo": False, "atualizado_em": datetime.now(timezone.utc).isoformat()})
        .eq("id", contact_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Contato nao encontrado")

    return {"detail": "Contato desativado"}



# ============================================================
# Tags
# ============================================================

@router.get("/tags")
async def list_tags(current_user: dict = Depends(get_current_user)):
    """Lista tags do workspace."""
    supabase = get_supabase()
    result = (
        supabase.table("contact_tags")
        .select("*")
        .eq("workspace_id", current_user["workspace_id"])
        .order("nome")
        .execute()
    )
    return result.data or []


@router.post("/tags")
async def create_tag(
    body: TagCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria uma tag."""
    supabase = get_supabase()
    result = (
        supabase.table("contact_tags")
        .insert({
            "workspace_id": current_user["workspace_id"],
            "nome": body.nome,
            "cor": body.cor,
        })
        .execute()
    )
    return result.data[0]


@router.put("/tags/{tag_id}")
async def update_tag(
    tag_id: str,
    body: TagUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza uma tag."""
    supabase = get_supabase()
    update_data = body.model_dump(exclude_none=True)
    result = (
        supabase.table("contact_tags")
        .update(update_data)
        .eq("id", tag_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Tag nao encontrada")
    return result.data[0]


@router.delete("/tags/{tag_id}")
async def delete_tag(
    tag_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove uma tag."""
    supabase = get_supabase()
    supabase.table("contacts_tags").delete().eq("tag_id", tag_id).execute()
    supabase.table("contact_tags").delete().eq("id", tag_id).eq("workspace_id", current_user["workspace_id"]).execute()
    return {"detail": "Tag removida"}


# ============================================================
# Deal Stages (Etapas do funil)
# ============================================================

@router.get("/stages")
async def list_stages(current_user: dict = Depends(get_current_user)):
    """Lista etapas do funil."""
    supabase = get_supabase()
    result = (
        supabase.table("deal_stages")
        .select("*")
        .eq("workspace_id", current_user["workspace_id"])
        .eq("ativo", True)
        .order("posicao")
        .execute()
    )
    return result.data or []


@router.post("/stages")
async def create_stage(
    body: StageCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria uma etapa do funil."""
    supabase = get_supabase()
    result = (
        supabase.table("deal_stages")
        .insert({
            "workspace_id": current_user["workspace_id"],
            "nome": body.nome,
            "posicao": body.posicao,
            "cor": body.cor,
        })
        .execute()
    )
    return result.data[0]


@router.put("/stages/{stage_id}")
async def update_stage(
    stage_id: str,
    body: StageUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza uma etapa."""
    supabase = get_supabase()
    update_data = body.model_dump(exclude_none=True)
    update_data["atualizado_em"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("deal_stages")
        .update(update_data)
        .eq("id", stage_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Etapa nao encontrada")
    return result.data[0]


@router.delete("/stages/{stage_id}")
async def delete_stage(
    stage_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Desativa uma etapa (soft-delete)."""
    supabase = get_supabase()
    # Verificar se ha deals nesta etapa
    deals = (
        supabase.table("deals")
        .select("id", count="exact")
        .eq("stage_id", stage_id)
        .eq("status", "aberto")
        .execute()
    )
    if deals.count and deals.count > 0:
        raise HTTPException(400, "Nao e possivel remover etapa com deals abertos. Mova os deals primeiro.")

    result = (
        supabase.table("deal_stages")
        .update({"ativo": False, "atualizado_em": datetime.now(timezone.utc).isoformat()})
        .eq("id", stage_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Etapa nao encontrada")
    return {"detail": "Etapa desativada"}


# ============================================================
# Deals
# ============================================================

@router.get("/deals")
async def list_deals(
    current_user: dict = Depends(get_current_user),
    status: str = Query("aberto"),
    stage_id: str = Query(None),
):
    """Lista deals agrupados por etapa (para kanban)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("deals")
        .select("*, deal_stages(id, nome, cor, posicao), contacts(id, nome, email, empresa)")
        .eq("workspace_id", workspace_id)
        .eq("status", status)
        .order("posicao_kanban")
    )

    if stage_id:
        query = query.eq("stage_id", stage_id)

    result = query.execute()
    return result.data or []


@router.post("/deals")
async def create_deal(
    body: DealCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria um deal/oportunidade."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    data = {
        "workspace_id": workspace_id,
        "titulo": body.titulo,
        "contact_id": body.contact_id,
        "stage_id": body.stage_id,
        "valor_centavos": body.valor_centavos,
        "moeda": body.moeda,
        "previsao_fechamento": body.previsao_fechamento,
        "responsavel_id": body.responsavel_id or current_user["id"],
        "notas": body.notas,
    }

    result = supabase.table("deals").insert(data).execute()
    return result.data[0]


@router.put("/deals/{deal_id}")
async def update_deal(
    deal_id: str,
    body: DealUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza um deal."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    update_data = body.model_dump(exclude_none=True)
    if body.status:
        update_data["status"] = body.status.value
    update_data["atualizado_em"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("deals")
        .update(update_data)
        .eq("id", deal_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Deal nao encontrado")
    return result.data[0]


@router.put("/deals/{deal_id}/move")
async def move_deal(
    deal_id: str,
    body: DealMoveRequest,
    current_user: dict = Depends(get_current_user),
):
    """Move deal entre etapas do funil (kanban drag-and-drop)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    result = (
        supabase.table("deals")
        .update({
            "stage_id": body.stage_id,
            "posicao_kanban": body.posicao_kanban,
            "atualizado_em": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", deal_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Deal nao encontrado")

    # Registrar atividade automatica
    try:
        stage = (
            supabase.table("deal_stages")
            .select("nome")
            .eq("id", body.stage_id)
            .limit(1)
            .execute()
        )
        stage_nome = stage.data[0]["nome"] if stage.data else "desconhecida"
        deal = result.data[0]
        supabase.table("activities").insert({
            "workspace_id": workspace_id,
            "contact_id": deal.get("contact_id"),
            "deal_id": deal_id,
            "user_id": current_user["id"],
            "tipo": "nota",
            "titulo": f"Deal movido para {stage_nome}",
            "descricao": f"Deal '{deal.get('titulo')}' movido para etapa '{stage_nome}'",
            "concluida": True,
        }).execute()
    except Exception as e:
        logger.warning(f"Falha ao registrar atividade de movimentacao: {e}")

    return result.data[0]


@router.delete("/deals/{deal_id}")
async def delete_deal(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove um deal."""
    supabase = get_supabase()
    # Remover atividades associadas primeiro
    supabase.table("activities").delete().eq("deal_id", deal_id).execute()
    result = (
        supabase.table("deals")
        .delete()
        .eq("id", deal_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Deal nao encontrado")
    return {"detail": "Deal removido"}


# ============================================================
# Atividades
# ============================================================

@router.get("/activities")
async def list_activities(
    current_user: dict = Depends(get_current_user),
    contact_id: str = Query(None),
    deal_id: str = Query(None),
    tipo: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
):
    """Lista atividades com filtros."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("activities")
        .select("*, contacts(id, nome), deals(id, titulo)", count="exact")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
    )

    if contact_id:
        query = query.eq("contact_id", contact_id)
    if deal_id:
        query = query.eq("deal_id", deal_id)
    if tipo:
        query = query.eq("tipo", tipo)

    offset = (page - 1) * per_page
    query = query.range(offset, offset + per_page - 1)

    result = query.execute()
    return {
        "data": result.data or [],
        "total": result.count or 0,
        "page": page,
        "per_page": per_page,
    }


@router.post("/activities")
async def create_activity(
    body: ActivityCreate,
    current_user: dict = Depends(get_current_user),
):
    """Cria uma atividade (nota, email, ligacao, reuniao, tarefa)."""
    supabase = get_supabase()

    if not body.contact_id and not body.deal_id:
        raise HTTPException(400, "Informe contact_id ou deal_id")

    data = {
        "workspace_id": current_user["workspace_id"],
        "contact_id": body.contact_id,
        "deal_id": body.deal_id,
        "user_id": current_user["id"],
        "tipo": body.tipo.value,
        "titulo": body.titulo,
        "descricao": body.descricao,
        "data_atividade": body.data_atividade or datetime.now(timezone.utc).isoformat(),
        "concluida": body.concluida,
    }

    result = supabase.table("activities").insert(data).execute()
    return result.data[0]


@router.put("/activities/{activity_id}")
async def update_activity(
    activity_id: str,
    body: ActivityUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza uma atividade."""
    supabase = get_supabase()
    update_data = body.model_dump(exclude_none=True)
    result = (
        supabase.table("activities")
        .update(update_data)
        .eq("id", activity_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Atividade nao encontrada")
    return result.data[0]


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove uma atividade."""
    supabase = get_supabase()
    result = (
        supabase.table("activities")
        .delete()
        .eq("id", activity_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(404, "Atividade nao encontrada")
    return {"detail": "Atividade removida"}
