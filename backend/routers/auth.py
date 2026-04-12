import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends

from core.schemas import (
    LoginRequest, TokenResponse, RefreshRequest, AccessTokenResponse,
    InviteAccept, PasswordChangeRequest, SignupRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
)
from core.auth import (
    verify_password,
    hash_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from core.db import get_supabase
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

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


# === Signup público ===

@router.post("/signup", response_model=TokenResponse, status_code=201)
async def signup(body: SignupRequest):
    """Cria workspace + user admin + subscription trial. Retorna tokens para login automático."""
    supabase = get_supabase()

    # Verificar email duplicado
    existing = supabase.table("users").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")

    # Criar workspace
    ws_data = {
        "nome": body.workspace_nome,
        "segmento": body.segmento,
        "documento_titular": body.documento,
        "telefone": body.telefone,
        "email_cobranca": body.email,
        "onboarding_completed": False,
    }
    ws_result = supabase.table("workspaces").insert(ws_data).execute()
    workspace = ws_result.data[0]

    # Criar user admin
    user_data = {
        "workspace_id": workspace["id"],
        "nome": body.nome,
        "email": body.email,
        "senha_hash": hash_password(body.senha),
        "papel": "admin",
        "ativo": True,
    }
    user_result = supabase.table("users").insert(user_data).execute()
    user = user_result.data[0]

    # Buscar plano free para subscription trial
    plan_result = supabase.table("plans").select("id").eq("slug", "starter").execute()
    if plan_result.data:
        plan_id = plan_result.data[0]["id"]
        trial_end = (datetime.now(timezone.utc) + timedelta(days=14)).isoformat()
        supabase.table("subscriptions").insert({
            "workspace_id": workspace["id"],
            "plan_id": plan_id,
            "status": "trial",
            "trial_ends_at": trial_end,
            "current_period_start": datetime.now(timezone.utc).isoformat(),
            "current_period_end": trial_end,
        }).execute()

    # Retorna tokens para login automático
    token_data = {"sub": user["id"], "workspace_id": workspace["id"], "papel": "admin"}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


# === Forgot Password ===

@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest):
    """Envia email com token de reset de senha."""
    supabase = get_supabase()

    result = supabase.table("users").select("id, nome, email").eq("email", body.email).eq("ativo", True).execute()

    # Sempre retorna sucesso (não revelar se email existe)
    if not result.data:
        return {"detail": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."}

    user = result.data[0]
    reset_token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    # Salvar token no banco
    supabase.table("users").update({
        "reset_token": reset_token,
        "reset_token_expires_at": expires_at,
    }).eq("id", user["id"]).execute()

    # Enviar email via Resend
    reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"
    try:
        import resend
        resend.api_key = settings.resend_api_key
        if settings.resend_api_key:
            resend.Emails.send({
                "from": "Usina do Tempo <noreply@usinadotempo.com.br>",
                "to": [user["email"]],
                "subject": "Redefinir sua senha — Usina do Tempo",
                "html": f"""
                    <h2>Olá, {user['nome']}!</h2>
                    <p>Recebemos uma solicitação para redefinir sua senha.</p>
                    <p><a href="{reset_url}" style="background:#4F46E5;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;display:inline-block;">Redefinir senha</a></p>
                    <p>Este link expira em 1 hora.</p>
                    <p>Se você não solicitou isso, ignore este e-mail.</p>
                """,
            })
    except Exception as e:
        logger.warning(f"Erro ao enviar email de reset: {e}")

    return {"detail": "Se o e-mail estiver cadastrado, você receberá instruções para redefinir sua senha."}


# === Reset Password ===

@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """Redefine a senha usando token de reset."""
    supabase = get_supabase()

    result = (
        supabase.table("users")
        .select("id, reset_token, reset_token_expires_at")
        .eq("reset_token", body.token)
        .eq("ativo", True)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=400, detail="Token inválido ou expirado")

    user = result.data[0]

    # Verificar expiração
    if user.get("reset_token_expires_at"):
        expires = datetime.fromisoformat(user["reset_token_expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(status_code=400, detail="Token expirado. Solicite um novo.")

    # Atualizar senha e limpar token
    supabase.table("users").update({
        "senha_hash": hash_password(body.nova_senha),
        "reset_token": None,
        "reset_token_expires_at": None,
    }).eq("id", user["id"]).execute()

    return {"detail": "Senha redefinida com sucesso. Faça login com sua nova senha."}