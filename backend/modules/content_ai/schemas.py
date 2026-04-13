from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class TipoConteudoAI(str, Enum):
    copy_ads = "copy_ads"
    legenda = "legenda"
    roteiro = "roteiro"
    artigo = "artigo"
    resposta_comentario = "resposta_comentario"
    email_marketing = "email_marketing"


class TomVoz(str, Enum):
    profissional = "profissional"
    casual = "casual"
    divertido = "divertido"
    formal = "formal"
    inspirador = "inspirador"
    educativo = "educativo"
    persuasivo = "persuasivo"
    tecnico = "tecnico"


# === Requests ===

class GenerateContentRequest(BaseModel):
    tipo: TipoConteudoAI
    tom_voz: TomVoz = TomVoz.profissional
    idioma: str = "pt-BR"
    negocio_id: Optional[str] = None
    template_id: Optional[str] = None
    prompt_usuario: Optional[str] = Field(None, max_length=2000)
    contexto: Optional[dict] = Field(default_factory=dict)
    quantidade: int = Field(default=1, ge=1, le=5)
    plataforma: Optional[str] = None  # meta, google, tiktok, instagram, youtube, linkedin


class TemplateCreateRequest(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    tipo: TipoConteudoAI
    tom_voz: Optional[str] = None
    idioma: str = "pt-BR"
    prompt_sistema: Optional[str] = Field(None, max_length=5000)
    prompt_template: str = Field(min_length=10, max_length=10000)
    variaveis: Optional[list[dict]] = None


class TemplateUpdateRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    tom_voz: Optional[str] = None
    prompt_sistema: Optional[str] = Field(None, max_length=5000)
    prompt_template: Optional[str] = Field(None, min_length=10, max_length=10000)
    variaveis: Optional[list[dict]] = None
    ativo: Optional[bool] = None


class RateContentRequest(BaseModel):
    avaliacao: int = Field(ge=1, le=5)


class UseInVideoEngineRequest(BaseModel):
    generated_content_id: str
    negocio_id: str


# === Responses ===

class ContentTemplateResponse(BaseModel):
    id: str
    workspace_id: str
    nome: str
    tipo: str
    tom_voz: Optional[str] = None
    idioma: str = "pt-BR"
    prompt_sistema: Optional[str] = None
    prompt_template: str
    variaveis: Optional[list] = None
    ativo: bool = True
    criado_em: str
    atualizado_em: str


class ContentRequestResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: Optional[str] = None
    template_id: Optional[str] = None
    negocio_id: Optional[str] = None
    tipo: str
    tom_voz: str = "profissional"
    idioma: str = "pt-BR"
    prompt_usuario: Optional[str] = None
    contexto: Optional[dict] = None
    quantidade: int = 1
    status: str = "pending"
    erro_msg: Optional[str] = None
    criado_em: str


class GeneratedContentResponse(BaseModel):
    id: str
    request_id: str
    workspace_id: str
    negocio_id: Optional[str] = None
    tipo: str
    titulo: Optional[str] = None
    conteudo: str
    metadata: Optional[dict] = None
    tokens_usados: int = 0
    avaliacao: Optional[int] = None
    usado_em: Optional[str] = None
    criado_em: str


class GenerateResultResponse(BaseModel):
    request_id: str
    status: str
    contents: list[GeneratedContentResponse] = []
