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
