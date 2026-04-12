from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from modules.video_engine.schemas import (
    NegocioCreate,
    NegocioUpdate,
    NegocioResponse,
    Plataforma,
    ScheduleItem,
    StatusNegocio,
)
from core.auth import get_current_user, require_role
from core.db import get_supabase

router = APIRouter(prefix="/negocios", tags=["Negócios"])


@router.get("/schedule/today", response_model=list[ScheduleItem])
async def schedule_today(current_user: dict = Depends(get_current_user)):
    """Timeline do dia: todos os negócios ativos do workspace com seus horários."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    result = (
        supabase.table("negocios")
        .select("id, nome, horario_disparo, status, categoria, frequencia, dias_semana")
        .eq("workspace_id", workspace_id)
        .eq("status", "ativo")
        .order("horario_disparo")
        .execute()
    )

    hoje = datetime.now(timezone.utc).weekday()
    dia_semana_hoje = (hoje + 1) % 7

    timeline = []
    for neg in result.data:
        if neg.get("frequencia") != "diaria" and neg.get("dias_semana"):
            if dia_semana_hoje not in neg["dias_semana"]:
                continue

        timeline.append(
            ScheduleItem(
                hora=neg["horario_disparo"],
                negocio=neg["nome"],
                negocio_id=neg["id"],
                status="agendado",
                categoria=neg.get("categoria"),
            )
        )

    return timeline


@router.get("", response_model=list[NegocioResponse])
async def list_negocios(
    status: Optional[str] = Query(None, description="Filtrar por status: ativo, pausado, arquivado"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    current_user: dict = Depends(get_current_user),
):
    """Lista negócios do workspace com filtros opcionais."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = supabase.table("negocios").select("*").eq("workspace_id", workspace_id)

    if status:
        query = query.eq("status", status)
    if categoria:
        query = query.eq("categoria", categoria)

    result = query.order("criado_em", desc=True).execute()
    return result.data


@router.post("", response_model=NegocioResponse, status_code=201)
async def create_negocio(
    body: NegocioCreate,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Cria um novo negócio com validação completa."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Validar horário único por workspace
    existing = (
        supabase.table("negocios")
        .select("id, nome")
        .eq("workspace_id", workspace_id)
        .eq("horario_disparo", body.horario_disparo)
        .neq("status", "arquivado")
        .execute()
    )
    if existing.data:
        nome_conflito = existing.data[0]["nome"]
        raise HTTPException(
            status_code=409,
            detail=f"Horário {body.horario_disparo}h já está em uso pelo negócio '{nome_conflito}'",
        )

    now = datetime.now(timezone.utc).isoformat()
    neg_data = {
        "workspace_id": workspace_id,
        "nome": body.nome,
        "categoria": body.categoria,
        "descricao": body.descricao,
        "publico_alvo": body.publico_alvo,
        "funcionalidades": body.funcionalidades,
        "diferenciais": body.diferenciais,
        "cta": body.cta,
        "link_download": body.link_download,
        "plataformas": [p.value for p in body.plataformas],
        "formato_instagram": body.formato_instagram,
        "formato_youtube": body.formato_youtube.value if body.formato_youtube else None,
        "frequencia": body.frequencia.value,
        "horario_disparo": body.horario_disparo,
        "dias_semana": body.dias_semana,
        "tom_voz": body.tom_voz,
        "status": "ativo",
        "keywords": body.keywords,
        "criado_em": now,
        "atualizado_em": now,
    }

    result = supabase.table("negocios").insert(neg_data).execute()
    return result.data[0]


@router.get("/{negocio_id}", response_model=NegocioResponse)
async def get_negocio(negocio_id: str, current_user: dict = Depends(get_current_user)):
    """Detalhes de um negócio específico."""
    supabase = get_supabase()
    result = (
        supabase.table("negocios")
        .select("*")
        .eq("id", negocio_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Negócio não encontrado")

    return result.data[0]


@router.put("/{negocio_id}", response_model=NegocioResponse)
async def update_negocio(
    negocio_id: str,
    body: NegocioUpdate,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Atualiza configurações de um negócio."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = (
        supabase.table("negocios")
        .select("*")
        .eq("id", negocio_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Negócio não encontrado")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    if "horario_disparo" in update_data:
        conflito = (
            supabase.table("negocios")
            .select("id, nome")
            .eq("workspace_id", workspace_id)
            .eq("horario_disparo", update_data["horario_disparo"])
            .neq("id", negocio_id)
            .neq("status", "arquivado")
            .execute()
        )
        if conflito.data:
            nome_conflito = conflito.data[0]["nome"]
            raise HTTPException(
                status_code=409,
                detail=f"Horário {update_data['horario_disparo']}h já está em uso pelo negócio '{nome_conflito}'",
            )

    if "plataformas" in update_data:
        plataformas = update_data["plataformas"]
        formato_youtube = update_data.get("formato_youtube") or existing.data[0].get("formato_youtube")
        if "youtube" in [p.value if hasattr(p, "value") else p for p in plataformas] and not formato_youtube:
            raise HTTPException(
                status_code=422,
                detail="formato_youtube é obrigatório quando YouTube está nas plataformas",
            )
        update_data["plataformas"] = [p.value if hasattr(p, "value") else p for p in plataformas]

    if "formato_youtube" in update_data and update_data["formato_youtube"]:
        fmt = update_data["formato_youtube"]
        update_data["formato_youtube"] = fmt.value if hasattr(fmt, "value") else fmt
    if "frequencia" in update_data and update_data["frequencia"]:
        freq = update_data["frequencia"]
        update_data["frequencia"] = freq.value if hasattr(freq, "value") else freq
    if "status" in update_data and update_data["status"]:
        st = update_data["status"]
        update_data["status"] = st.value if hasattr(st, "value") else st

    update_data["atualizado_em"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("negocios")
        .update(update_data)
        .eq("id", negocio_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return result.data[0]


@router.delete("/{negocio_id}", status_code=200)
async def delete_negocio(
    negocio_id: str,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Arquiva um negócio (soft delete)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = (
        supabase.table("negocios")
        .select("id, status")
        .eq("id", negocio_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Negócio não encontrado")

    if existing.data[0]["status"] == "arquivado":
        raise HTTPException(status_code=400, detail="Negócio já está arquivado")

    supabase.table("negocios").update({
        "status": "arquivado",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", negocio_id).eq("workspace_id", workspace_id).execute()

    return {"detail": "Negócio arquivado com sucesso"}


@router.get("/{negocio_id}/history")
async def negocio_history(
    negocio_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Histórico de vídeos gerados para o negócio."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    neg_result = (
        supabase.table("negocios")
        .select("id")
        .eq("id", negocio_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not neg_result.data:
        raise HTTPException(status_code=404, detail="Negócio não encontrado")

    videos = (
        supabase.table("videos")
        .select("*, conteudos(titulo, tipo_conteudo, roteiro)")
        .eq("negocio_id", negocio_id)
        .order("criado_em", desc=True)
        .execute()
    )

    return videos.data
