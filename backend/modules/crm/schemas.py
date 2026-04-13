from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum


# === Enums ===

class OrigemContato(str, Enum):
    site = "site"
    indicacao = "indicacao"
    linkedin = "linkedin"
    importacao = "importacao"
    manual = "manual"
    outro = "outro"


class TipoAtividade(str, Enum):
    nota = "nota"
    email = "email"
    ligacao = "ligacao"
    reuniao = "reuniao"
    tarefa = "tarefa"


class StatusDeal(str, Enum):
    aberto = "aberto"
    ganho = "ganho"
    perdido = "perdido"


# === Contacts ===

class ContactCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    email: Optional[str] = None
    telefone: Optional[str] = Field(None, max_length=30)
    empresa: Optional[str] = Field(None, max_length=255)
    cargo: Optional[str] = Field(None, max_length=255)
    origem: OrigemContato = OrigemContato.manual
    notas: Optional[str] = None
    dados_extras: Optional[dict] = None
    tag_ids: Optional[list[str]] = None


class ContactUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = None
    telefone: Optional[str] = Field(None, max_length=30)
    empresa: Optional[str] = Field(None, max_length=255)
    cargo: Optional[str] = Field(None, max_length=255)
    origem: Optional[OrigemContato] = None
    notas: Optional[str] = None
    dados_extras: Optional[dict] = None
    ativo: Optional[bool] = None
    tag_ids: Optional[list[str]] = None


# === Tags ===

class TagCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=100)
    cor: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class TagUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=100)
    cor: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")


# === Deal Stages ===

class StageCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    posicao: int = 0
    cor: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")


class StageUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    posicao: Optional[int] = None
    cor: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    ativo: Optional[bool] = None


# === Deals ===

class DealCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=255)
    contact_id: Optional[str] = None
    stage_id: str
    valor_centavos: int = 0
    moeda: str = "BRL"
    previsao_fechamento: Optional[str] = None
    responsavel_id: Optional[str] = None
    notas: Optional[str] = None


class DealUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    contact_id: Optional[str] = None
    stage_id: Optional[str] = None
    valor_centavos: Optional[int] = None
    status: Optional[StatusDeal] = None
    motivo_perda: Optional[str] = Field(None, max_length=500)
    previsao_fechamento: Optional[str] = None
    responsavel_id: Optional[str] = None
    notas: Optional[str] = None
    posicao_kanban: Optional[int] = None


class DealMoveRequest(BaseModel):
    stage_id: str
    posicao_kanban: int = 0


# === Activities ===

class ActivityCreate(BaseModel):
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    tipo: TipoAtividade
    titulo: Optional[str] = Field(None, max_length=255)
    descricao: Optional[str] = None
    data_atividade: Optional[str] = None
    concluida: bool = False


class ActivityUpdate(BaseModel):
    titulo: Optional[str] = Field(None, max_length=255)
    descricao: Optional[str] = None
    concluida: Optional[bool] = None


# === Import ===

class ImportResult(BaseModel):
    total: int = 0
    criados: int = 0
    erros: int = 0
    detalhes_erros: list[str] = []
