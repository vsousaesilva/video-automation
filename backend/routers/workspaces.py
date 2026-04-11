from fastapi import APIRouter, Depends, HTTPException

from models.schemas import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, TokenResponse
from auth_deps import hash_password, create_access_token, create_refresh_token, get_current_user, require_role
from db import get_supabase

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.post("", response_model=TokenResponse, status_code=201)
async def create_workspace(body: WorkspaceCreate):
    supabase = get_supabase()

    # Verifica se e-mail já está em uso
    existing = supabase.table("users").select("id").eq("email", body.admin_email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    # Cria workspace
    ws_data = {
        "nome": body.nome,
        "segmento": body.segmento,
        "tom_voz": body.tom_voz,
        "idioma": body.idioma,
        "cor_primaria": body.cor_primaria,
        "cor_secundaria": body.cor_secundaria,
    }
    ws_result = supabase.table("workspaces").insert(ws_data).execute()
    workspace = ws_result.data[0]

    # Cria usuário admin
    user_data = {
        "workspace_id": workspace["id"],
        "nome": body.admin_nome,
        "email": body.admin_email,
        "senha_hash": hash_password(body.admin_senha),
        "papel": "admin",
        "ativo": True,
    }
    user_result = supabase.table("users").insert(user_data).execute()
    user = user_result.data[0]

    # Retorna tokens para login automático
    token_data = {"sub": user["id"], "workspace_id": workspace["id"], "papel": "admin"}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.get("/me", response_model=WorkspaceResponse)
async def get_my_workspace(current_user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = supabase.table("workspaces").select("*").eq("id", current_user["workspace_id"]).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Workspace não encontrado")

    return result.data[0]


@router.put("/me", response_model=WorkspaceResponse)
async def update_my_workspace(
    body: WorkspaceUpdate,
    current_user: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    update_data = body.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    result = (
        supabase.table("workspaces")
        .update(update_data)
        .eq("id", current_user["workspace_id"])
        .execute()
    )

    return result.data[0]