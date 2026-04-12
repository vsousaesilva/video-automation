from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from enum import Enum


# === Enums ===

class Papel(str, Enum):
    admin = "admin"
    editor = "editor"
    viewer = "viewer"


# === Auth ===

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# === Workspace ===

class WorkspaceCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    segmento: Optional[str] = None
    tom_voz: Optional[str] = None
    idioma: str = "pt-BR"
    cor_primaria: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    cor_secundaria: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    admin_nome: str = Field(min_length=2, max_length=255)
    admin_email: EmailStr
    admin_senha: str = Field(min_length=6)


class WorkspaceUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    segmento: Optional[str] = None
    tom_voz: Optional[str] = None
    idioma: Optional[str] = None
    cor_primaria: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    cor_secundaria: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


class WorkspaceResponse(BaseModel):
    id: str
    nome: str
    segmento: Optional[str] = None
    tom_voz: Optional[str] = None
    idioma: str
    logo_url: Optional[str] = None
    cor_primaria: Optional[str] = None
    cor_secundaria: Optional[str] = None
    criado_em: str


# === Usuários ===

class UserResponse(BaseModel):
    id: str
    nome: str
    email: str
    papel: str
    ativo: bool
    criado_em: str


class UserInvite(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    email: EmailStr
    papel: Papel = Papel.editor


class UserUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    papel: Optional[Papel] = None
    ativo: Optional[bool] = None


class InviteAccept(BaseModel):
    token: str
    senha: str = Field(min_length=6)


class PasswordChangeRequest(BaseModel):
    senha_atual: str = Field(min_length=6)
    nova_senha: str = Field(min_length=6)


# === Signup ===

class SignupRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    email: EmailStr
    senha: str = Field(min_length=6)
    workspace_nome: str = Field(min_length=2, max_length=255)
    segmento: Optional[str] = None
    documento: Optional[str] = Field(None, max_length=18)
    telefone: Optional[str] = Field(None, max_length=20)


# === Forgot / Reset Password ===

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str = Field(min_length=6)


# === Billing ===

class PlanResponse(BaseModel):
    id: str
    slug: str
    nome: str
    descricao: Optional[str] = None
    modulos: list = []
    max_negocios: int = 1
    max_users: int = 1
    max_videos_mes: Optional[int] = None
    max_conteudos_mes: Optional[int] = None
    max_campanhas: Optional[int] = None
    max_contatos_crm: Optional[int] = None
    max_benchmarks_mes: Optional[int] = None
    storage_max_gb: Optional[float] = None
    preco_centavos: int = 0
    intervalo: str = "mensal"
    ativo: bool = True


class SubscriptionResponse(BaseModel):
    id: str
    workspace_id: str
    plan_id: str
    status: str
    trial_ends_at: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    canceled_at: Optional[str] = None
    criado_em: str
    plans: Optional[PlanResponse] = None


class CheckoutRequest(BaseModel):
    plan_slug: str


class UsageResponse(BaseModel):
    videos_gerados: int = 0
    videos_publicados: int = 0
    conteudos_gerados: int = 0
    campanhas_criadas: int = 0
    contatos_crm: int = 0
    benchmarks_executados: int = 0
    storage_bytes: int = 0
    api_calls: int = 0


class InvoiceResponse(BaseModel):
    id: str
    subscription_id: str
    workspace_id: str
    asaas_payment_id: Optional[str] = None
    valor_centavos: int
    status: str
    url_boleto: Optional[str] = None
    url_pix: Optional[str] = None
    vencimento: Optional[str] = None
    pago_em: Optional[str] = None
    criado_em: str
