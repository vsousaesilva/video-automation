from fastapi import APIRouter, HTTPException, Depends

from core.schemas import LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse, InviteAccept, PasswordChangeRequest
from core.auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from core.db import get_supabase

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("email", body.email).eq("ativo", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    user = result.data[0]

    if not user.get("senha_hash"):
        raise HTTPException(status_code=401, detail="Usuário ainda não definiu senha. Aceite o convite primeiro.")

    if not verify_password(body.password, user["senha_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token_data = {"sub": user["id"], "workspace_id": user["workspace_id"], "papel": user["papel"]}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(body: RefreshRequest):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    user_id = payload.get("sub")

    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("id", user_id).eq("ativo", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou desativado")

    user = result.data[0]
    token_data = {"sub": user["id"], "workspace_id": user["workspace_id"], "papel": user["papel"]}
    return AccessTokenResponse(access_token=create_access_token(token_data))


@router.post("/logout", status_code=204)
async def logout(current_user: dict = Depends(get_current_user)):
    # JWT é stateless — o logout real acontece no frontend descartando o token.
    # Endpoint existe para manter a interface REST consistente.
    return None


@router.put("/change-password")
async def change_password(
    body: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
):
    """Altera a senha do usuário autenticado."""
    if not verify_password(body.senha_atual, current_user["senha_hash"]):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    supabase = get_supabase()
    supabase.table("users").update({
        "senha_hash": hash_password(body.nova_senha),
    }).eq("id", current_user["id"]).execute()

    return {"detail": "Senha alterada com sucesso"}


@router.post("/accept-invite")
async def accept_invite(body: InviteAccept):
    payload = decode_token(body.token, expected_type="invite")
    email = payload.get("email")
    workspace_id = payload.get("workspace_id")

    supabase = get_supabase()
    result = (
        supabase.table("users")
        .select("*")
        .eq("email", email)
        .eq("workspace_id", workspace_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Convite não encontrado")

    user = result.data[0]
    if user.get("senha_hash"):
        raise HTTPException(status_code=400, detail="Convite já foi aceito")

    supabase.table("users").update({"senha_hash": hash_password(body.senha), "ativo": True}).eq("id", user["id"]).execute()

    return {"detail": "Conta ativada com sucesso. Faça login."}