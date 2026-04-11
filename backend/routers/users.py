from fastapi import APIRouter, Depends, HTTPException

from models.schemas import UserResponse, UserInvite, UserUpdate
from auth_deps import get_current_user, require_role, create_invite_token
from config import get_settings
from db import get_supabase

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.get("", response_model=list[UserResponse])
async def list_users(current_user: dict = Depends(require_role(["admin"]))):
    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("id, nome, email, papel, ativo, criado_em")
        .eq("workspace_id", current_user["workspace_id"])
        .execute()
    )
    return result.data


@router.post("/invite", status_code=201)
async def invite_user(
    body: UserInvite,
    current_user: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    settings = get_settings()
    workspace_id = current_user["workspace_id"]

    # Verifica duplicata no workspace
    existing = (
        supabase.table("users")
        .select("id")
        .eq("email", body.email)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if existing.data:
        raise HTTPException(status_code=409, detail="Usuário já existe neste workspace")

    # Cria usuário inativo (sem senha)
    user_data = {
        "workspace_id": workspace_id,
        "nome": body.nome,
        "email": body.email,
        "papel": body.papel.value,
        "ativo": False,
    }
    supabase.table("users").insert(user_data).execute()

    # Gera token de convite
    invite_token = create_invite_token(body.email, workspace_id)
    invite_link = f"{settings.base_url}/auth/accept-invite?token={invite_token}"

    # TODO: Sessão futura — enviar e-mail via Resend
    # Por ora, retorna o link para teste manual
    return {
        "detail": "Convite criado com sucesso",
        "invite_link": invite_link,
    }


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UserUpdate,
    current_user: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Verifica se o usuário pertence ao workspace
    existing = (
        supabase.table("users")
        .select("*")
        .eq("id", user_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Admin não pode rebaixar a si mesmo
    if user_id == current_user["id"] and body.papel and body.papel.value != "admin":
        raise HTTPException(status_code=400, detail="Não é possível rebaixar o próprio papel")

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Converte enum para string
    if "papel" in update_data and update_data["papel"]:
        update_data["papel"] = update_data["papel"].value

    result = (
        supabase.table("users")
        .update(update_data)
        .eq("id", user_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    return result.data[0]


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_role(["admin"])),
):
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Não é possível remover a si mesmo")

    existing = (
        supabase.table("users")
        .select("id")
        .eq("id", user_id)
        .eq("workspace_id", workspace_id)
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    supabase.table("users").delete().eq("id", user_id).eq("workspace_id", workspace_id).execute()
    return None