from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


# === Enums ===

class Plataforma(str, Enum):
    meta = "meta"
    google = "google"
    tiktok = "tiktok"


class StatusAdAccount(str, Enum):
    ativo = "ativo"
    expirado = "expirado"
    removido = "removido"


class EscopoRegra(str, Enum):
    campaign = "campaign"
    ad_set = "ad_set"
    ad = "ad"


class AcaoRegra(str, Enum):
    pause = "pause"
    activate = "activate"
    adjust_budget = "adjust_budget"
    notify = "notify"


# === Ad Accounts ===

class AdAccountConnect(BaseModel):
    """Conecta conta de ads via token OAuth ja trocado pelo frontend."""
    plataforma: Plataforma = Plataforma.meta
    external_id: str = Field(min_length=1, max_length=100)
    nome: Optional[str] = Field(None, max_length=255)
    access_token: str = Field(min_length=10)
    refresh_token: Optional[str] = None
    token_expira_em: Optional[str] = None  # ISO datetime
    moeda: Optional[str] = "BRL"
    fuso: Optional[str] = None


class AdAccountUpdate(BaseModel):
    nome: Optional[str] = Field(None, max_length=255)
    status: Optional[StatusAdAccount] = None


# === Campaigns ===

class CampaignAction(BaseModel):
    """Pausar/ativar campanha."""
    action: str = Field(pattern="^(pause|activate)$")


class CampaignBudgetUpdate(BaseModel):
    orcamento_diario_centavos: Optional[int] = Field(None, ge=0)
    orcamento_total_centavos: Optional[int] = Field(None, ge=0)


# === Rules ===

class RegraCondicao(BaseModel):
    metrica: str  # cpa, roas, ctr, gasto, cliques, impressoes
    operador: str = Field(pattern="^(>|<|>=|<=|==)$")
    valor: float
    periodo_dias: int = Field(default=1, ge=1, le=30)


class AdRuleCreate(BaseModel):
    nome: str = Field(min_length=1, max_length=255)
    ad_account_id: Optional[str] = None
    escopo: EscopoRegra = EscopoRegra.campaign
    escopo_ids: list[str] = []
    condicao: RegraCondicao
    acao: AcaoRegra
    acao_params: dict[str, Any] = {}
    ativa: bool = True


class AdRuleUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    condicao: Optional[RegraCondicao] = None
    acao: Optional[AcaoRegra] = None
    acao_params: Optional[dict[str, Any]] = None
    escopo_ids: Optional[list[str]] = None
    ativa: Optional[bool] = None
