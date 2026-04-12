from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse

from modules.video_engine.schemas import MediaUploadResponse, MediaUpdate
from core.auth import get_current_user, require_role
from core.db import get_supabase
from modules.video_engine.services.storage import (
    validate_file,
    build_storage_path,
    upload_to_storage,
    delete_from_storage,
)
from modules.video_engine.services.media_selector import select_media_for_script

router = APIRouter(prefix="/media", tags=["Banco de Imagens"])


@router.post("/upload", response_model=MediaUploadResponse, status_code=201)
async def upload_media(
    file: UploadFile = File(...),
    negocio_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None, description='JSON array de tags, ex: ["produto","screenshot"]'),
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Upload de arquivo de mídia (imagem ou vídeo) para o banco do negócio ou workspace."""
    workspace_id = current_user["workspace_id"]
    supabase = get_supabase()

    # Validar que o app pertence ao workspace (se informado)
    if negocio_id:
        app_result = (
            supabase.table("negocios")
            .select("id")
            .eq("id", negocio_id)
            .eq("workspace_id", workspace_id)
            .execute()
        )
        if not app_result.data:
            raise HTTPException(status_code=404, detail="Negócio não encontrado neste workspace")

    # Ler conteudo do arquivo
    file_bytes = await file.read()
    file_size = len(file_bytes)
    content_type = file.content_type or "application/octet-stream"

    # Validar tipo, extensao e tamanho
    try:
        tipo = validate_file(file.filename or "unnamed", content_type, file_size)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Upload para o Storage
    storage_path = build_storage_path(workspace_id, negocio_id, file.filename or "unnamed")

    try:
        public_url = await upload_to_storage(file_bytes, storage_path, content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao fazer upload: {str(e)}")

    # Parsear tags
    import json
    parsed_tags = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
            if not isinstance(parsed_tags, list):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=422, detail="tags deve ser um JSON array valido")

    # Inserir registro no banco
    asset_data = {
        "workspace_id": workspace_id,
        "negocio_id": negocio_id,
        "nome": file.filename or "unnamed",
        "url_storage": public_url,
        "tipo": tipo,
        "tags": parsed_tags,
        "tamanho_bytes": file_size,
        "ativo": True,
    }

    result = supabase.table("media_assets").insert(asset_data).execute()
    return result.data[0]


@router.get("", response_model=list[MediaUploadResponse])
async def list_media(
    negocio_id: Optional[str] = Query(None, description="Filtrar por negócio"),
    tipo: Optional[str] = Query(None, description="Filtrar por tipo: imagem ou video"),
    tag: Optional[str] = Query(None, description="Filtrar por tag (contem)"),
    apenas_workspace: bool = Query(False, description="Apenas assets globais do workspace"),
    current_user: dict = Depends(get_current_user),
):
    """Lista assets com filtros (app_id, workspace global, tipo, tags)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("media_assets")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("ativo", True)
    )

    if apenas_workspace:
        query = query.is_("negocio_id", "null")
    elif negocio_id:
        query = query.eq("negocio_id", negocio_id)

    if tipo:
        query = query.eq("tipo", tipo)

    if tag:
        query = query.contains("tags", [tag])

    result = query.order("criado_em", desc=True).execute()
    return result.data


@router.get("/negocio/{negocio_id}", response_model=list[MediaUploadResponse])
async def list_negocio_media(
    negocio_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Assets do negócio especifico."""
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
        raise HTTPException(status_code=404, detail="Negócio não encontrado neste workspace")

    result = (
        supabase.table("media_assets")
        .select("*")
        .eq("negocio_id", negocio_id)
        .eq("ativo", True)
        .order("criado_em", desc=True)
        .execute()
    )

    return result.data


@router.put("/{media_id}", response_model=MediaUploadResponse)
async def update_media(
    media_id: str,
    body: MediaUpdate,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Atualiza nome e tags de um asset."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = (
        supabase.table("media_assets")
        .select("*")
        .eq("id", media_id)
        .eq("workspace_id", workspace_id)
        .eq("ativo", True)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Asset nao encontrado")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    result = (
        supabase.table("media_assets")
        .update(update_data)
        .eq("id", media_id)
        .execute()
    )

    return result.data[0]


@router.delete("/{media_id}", status_code=200)
async def delete_media(
    media_id: str,
    current_user: dict = Depends(require_role(["admin", "editor"])),
):
    """Remove asset e arquivo do Storage."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = (
        supabase.table("media_assets")
        .select("*")
        .eq("id", media_id)
        .eq("workspace_id", workspace_id)
        .eq("ativo", True)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Asset nao encontrado")

    asset = existing.data[0]

    # Remover do Storage
    try:
        await delete_from_storage(asset["url_storage"])
    except Exception:
        pass  # Log mas nao bloqueia a exclusao do registro

    # Soft delete
    supabase.table("media_assets").update({"ativo": False}).eq("id", media_id).execute()

    return {"detail": "Asset removido com sucesso"}


@router.post("/select")
async def select_media(
    negocio_id: str = Query(...),
    visual_keywords: str = Query(..., description='Keywords separadas por virgula'),
    min_count: int = Query(3, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
):
    """Endpoint de teste para o motor de selecao de midia."""
    workspace_id = current_user["workspace_id"]

    keywords = [k.strip() for k in visual_keywords.split(",") if k.strip()]
    if not keywords:
        raise HTTPException(status_code=422, detail="Informe ao menos uma keyword")

    urls = await select_media_for_script(
        negocio_id=negocio_id,
        workspace_id=workspace_id,
        visual_keywords=keywords,
        min_count=min_count,
    )

    return {"urls": urls, "total": len(urls), "keywords": keywords}
