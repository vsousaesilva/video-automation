from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from modules.video_engine.schemas import (
    AppCreate,
    AppUpdate,
    AppResponse,
    Plataforma,
    ScheduleItem,
    StatusApp,
)
from core.auth import get_current_user, require_role
from core.db import get_supabase

router = APIRouter(prefix="/apps", tags=["Aplicativos"])


@router.get("/schedule/today", response_model=list[ScheduleItem])
async def schedule_today(current_user: dict = Depends(get_current_user)):
    """Timeline do dia: todos os apps ativos do workspace com seus horários."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    result = (
        supabase.table("apps")
        .select("id, nome, horario_disparo, status, categoria, frequencia, dias_semana")
        .eq("workspace_id", workspace_id)
        .eq("status", "ativo")
        .order("horario_disparo")
        .execute()
    )

    hoje = datetime.now(timezone.utc).weekday()
    # Python weekday: 0=seg, mas nosso modelo: 0=dom, 1=seg...6=sab
    # Converter: Python seg=0 → nosso 1, dom=6 → nosso 0
    dia_semana_hoje = (hoje + 1) % 7

    timeline = []
    for app in result.data:
        # Verificar se o app roda hoje (baseado na frequência e dias_semana)
        if app.get("frequencia") != "diaria" and app.get("dias_semana"):
            if dia_semana_hoje not in app["dias_semana"]:
                continue

        timeline.append(
            ScheduleItem(
                hora=app["horario_disparo"],
                app=app["nome"],
                app_id=app["id"],
                status="agendado",
                categoria=app.get("categoria"),
            )
        )

    return timeline


@router.get("", response_model=list[AppResponse])
async def list_apps(
    status: Optional[str] = Query(None, description="Filtrar por status: ativo, pausado, arquivado"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoria"),
    current_user: dict = Depends(get_current_user),
):
    """Lista apps do workspace com filtros opcionais."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = supabase.table("apps").select("*").eq("workspace_id", workspace_id)

    if status:
        query = query.eq("status", status)
    if categoria:
        query = query.eq("categoria", categoria)

    result = query.order("criado_em", desc=True).execute()
    return result.data


@router.post("", response_model=AppResponse, status_code=201)
async def create_app(
    body: AppCreate,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Cria um novo app com validação completa."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Validar horário único por workspace
    existing = (
        supabase.table("apps")
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
            detail=f"Horário {body.horario_disparo}h já está em uso pelo app '{nome_conflito}'",
        )

    now = datetime.now(timezone.utc).isoformat()
    app_data = {
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

    result = supabase.table("apps").insert(app_data).execute()
    return result.data[0]


@router.get("/{app_id}", response_model=AppResponse)
async def get_app(app_id: str, current_user: dict = Depends(get_current_user)):
    """Detalhes de um app específico."""
    supabase = get_supabase()
    result = (
        supabase.table("apps")
        .select("*")
        .eq("id", app_id)
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="App não encontrado")

    return result.data[0]


@router.put("/{app_id}", response_model=AppResponse)
async def update_app(
    app_id: str,
    body: AppUpdate,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Atualiza configurações de um app."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Verificar se app existe
    existing = (
        supabase.table("apps")
        .select("*")
        .eq("id", app_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="App não encontrado")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Se está atualizando horário, validar unicidade
    if "horario_disparo" in update_data:
        conflito = (
            supabase.table("apps")
            .select("id, nome")
            .eq("workspace_id", workspace_id)
            .eq("horario_disparo", update_data["horario_disparo"])
            .neq("id", app_id)
            .neq("status", "arquivado")
            .execute()
        )
        if conflito.data:
            nome_conflito = conflito.data[0]["nome"]
            raise HTTPException(
                status_code=409,
                detail=f"Horário {update_data['horario_disparo']}h já está em uso pelo app '{nome_conflito}'",
            )

    # Se está atualizando plataformas, validar formato_youtube
    if "plataformas" in update_data:
        plataformas = update_data["plataformas"]
        formato_youtube = update_data.get("formato_youtube") or existing.data[0].get("formato_youtube")
        if "youtube" in [p.value if hasattr(p, "value") else p for p in plataformas] and not formato_youtube:
            raise HTTPException(
                status_code=422,
                detail="formato_youtube é obrigatório quando YouTube está nas plataformas",
            )
        update_data["plataformas"] = [p.value if hasattr(p, "value") else p for p in plataformas]

    # Converter enums para string
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
        supabase.table("apps")
        .update(update_data)
        .eq("id", app_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return result.data[0]


@router.delete("/{app_id}", status_code=200)
async def delete_app(
    app_id: str,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Arquiva um app (soft delete)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = (
        supabase.table("apps")
        .select("id, status")
        .eq("id", app_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="App não encontrado")

    if existing.data[0]["status"] == "arquivado":
        raise HTTPException(status_code=400, detail="App já está arquivado")

    supabase.table("apps").update({
        "status": "arquivado",
        "atualizado_em": datetime.now(timezone.utc).isoformat(),
    }).eq("id", app_id).eq("workspace_id", workspace_id).execute()

    return {"detail": "App arquivado com sucesso"}


@router.get("/{app_id}/history")
async def app_history(
    app_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Histórico de vídeos gerados para o app."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Verificar se app pertence ao workspace
    app_result = (
        supabase.table("apps")
        .select("id")
        .eq("id", app_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not app_result.data:
        raise HTTPException(status_code=404, detail="App não encontrado")

    # Buscar vídeos com dados do conteúdo
    videos = (
        supabase.table("videos")
        .select("*, conteudos(titulo, tipo_conteudo, roteiro)")
        .eq("app_id", app_id)
        .order("criado_em", desc=True)
        .execute()
    )

    return videos.data
