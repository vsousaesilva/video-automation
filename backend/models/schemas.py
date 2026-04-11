from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
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


# === Enums de App ===

class StatusApp(str, Enum):
    ativo = "ativo"
    pausado = "pausado"
    arquivado = "arquivado"


class Plataforma(str, Enum):
    instagram = "instagram"
    youtube = "youtube"


class FormatoYoutube(str, Enum):
    horizontal = "16_9"
    vertical = "9_16"
    ambos = "ambos"


class Frequencia(str, Enum):
    diaria = "diaria"
    tres_por_semana = "3x_semana"
    semanal = "semanal"


# === App ===

class AppCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    publico_alvo: Optional[str] = None
    funcionalidades: Optional[list[str]] = None
    diferenciais: Optional[list[str]] = None
    cta: Optional[str] = Field(None, max_length=255)
    link_download: Optional[str] = None
    plataformas: list[Plataforma] = Field(min_length=1)
    formato_instagram: str = "9_16"
    formato_youtube: Optional[FormatoYoutube] = None
    frequencia: Frequencia = Frequencia.diaria
    horario_disparo: int = Field(ge=0, le=23)
    dias_semana: Optional[list[int]] = Field(None, description="0=dom, 1=seg ... 6=sab")
    tom_voz: Optional[str] = None
    keywords: Optional[list[str]] = None

    def model_post_init(self, __context):
        if Plataforma.youtube in self.plataformas and self.formato_youtube is None:
            raise ValueError("formato_youtube é obrigatório quando YouTube está nas plataformas")
        if self.dias_semana:
            for d in self.dias_semana:
                if d < 0 or d > 6:
                    raise ValueError("dias_semana deve conter valores entre 0 e 6")


class AppUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=255)
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    publico_alvo: Optional[str] = None
    funcionalidades: Optional[list[str]] = None
    diferenciais: Optional[list[str]] = None
    cta: Optional[str] = Field(None, max_length=255)
    link_download: Optional[str] = None
    plataformas: Optional[list[Plataforma]] = None
    formato_instagram: Optional[str] = None
    formato_youtube: Optional[FormatoYoutube] = None
    frequencia: Optional[Frequencia] = None
    horario_disparo: Optional[int] = Field(None, ge=0, le=23)
    dias_semana: Optional[list[int]] = None
    tom_voz: Optional[str] = None
    status: Optional[StatusApp] = None
    keywords: Optional[list[str]] = None

    def model_post_init(self, __context):
        if self.plataformas and Plataforma.youtube in self.plataformas and self.formato_youtube is None:
            raise ValueError("formato_youtube é obrigatório quando YouTube está nas plataformas")
        if self.dias_semana:
            for d in self.dias_semana:
                if d < 0 or d > 6:
                    raise ValueError("dias_semana deve conter valores entre 0 e 6")


class AppResponse(BaseModel):
    id: str
    workspace_id: str
    nome: str
    categoria: Optional[str] = None
    descricao: Optional[str] = None
    publico_alvo: Optional[str] = None
    funcionalidades: Optional[list] = None
    diferenciais: Optional[list] = None
    cta: Optional[str] = None
    link_download: Optional[str] = None
    plataformas: Optional[list] = None
    formato_instagram: Optional[str] = None
    formato_youtube: Optional[str] = None
    frequencia: Optional[str] = None
    horario_disparo: Optional[int] = None
    dias_semana: Optional[list] = None
    tom_voz: Optional[str] = None
    status: str = "ativo"
    keywords: Optional[list] = None
    criado_em: str
    atualizado_em: str


class ScheduleItem(BaseModel):
    hora: int
    app: str
    app_id: str
    status: str
    categoria: Optional[str] = None


# === Enums de Media ===

class TipoMedia(str, Enum):
    imagem = "imagem"
    video = "video"


# === Media Assets ===

class MediaUploadResponse(BaseModel):
    id: str
    workspace_id: str
    app_id: Optional[str] = None
    nome: str
    url_storage: str
    tipo: str
    tags: Optional[list[str]] = None
    tamanho_bytes: Optional[int] = None
    largura: Optional[int] = None
    altura: Optional[int] = None
    ativo: bool = True
    criado_em: str


class MediaUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    tags: Optional[list[str]] = None


class MediaListParams(BaseModel):
    app_id: Optional[str] = None
    tipo: Optional[TipoMedia] = None
    tags: Optional[list[str]] = None
    apenas_workspace: bool = False


# === Enums de Conteúdo ===

class TipoConteudo(str, Enum):
    problema_solucao = "problema_solucao"
    tutorial_rapido = "tutorial_rapido"
    beneficio_destaque = "beneficio_destaque"
    prova_social = "prova_social"
    comparativo = "comparativo"
    curiosidade_nicho = "curiosidade_nicho"


class StatusConteudo(str, Enum):
    gerado = "gerado"
    processando_video = "processando_video"
    aguardando_aprovacao = "aguardando_aprovacao"
    aprovado = "aprovado"
    rejeitado = "rejeitado"
    publicado = "publicado"
    erro = "erro"


# === Conteúdo ===

class ContentOutput(BaseModel):
    roteiro: str
    titulo: str
    descricao_youtube: str
    descricao_instagram: str
    hashtags_youtube: list[str]
    hashtags_instagram: list[str]
    keywords_visuais: list[str]
    keywords_seo: list[str]
    tipo_conteudo: str


class ConteudoResponse(BaseModel):
    id: str
    app_id: str
    tipo_conteudo: Optional[str] = None
    roteiro: Optional[str] = None
    titulo: Optional[str] = None
    descricao_youtube: Optional[str] = None
    descricao_instagram: Optional[str] = None
    hashtags_youtube: Optional[list] = None
    hashtags_instagram: Optional[list] = None
    keywords_visuais: Optional[list] = None
    keywords_seo: Optional[list] = None
    status: str = "gerado"
    erro_msg: Optional[str] = None
    criado_em: str


# === Pipeline ===

class PipelineTriggerRequest(BaseModel):
    hora_atual: int = Field(ge=0, le=23)


class PipelineTriggerResponse(BaseModel):
    status: str
    apps_triggered: list[str]


# === Vídeos ===

class VideoResponse(BaseModel):
    id: str
    conteudo_id: Optional[str] = None
    app_id: str
    url_storage_vertical: Optional[str] = None
    duracao_vertical_segundos: Optional[int] = None
    url_storage_horizontal: Optional[str] = None
    duracao_horizontal_segundos: Optional[int] = None
    tamanho_bytes_total: Optional[int] = None
    status: str = "processando"
    aprovado_por: Optional[str] = None
    aprovado_via: Optional[str] = None
    aprovado_em: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    url_youtube: Optional[str] = None
    url_instagram: Optional[str] = None
    publicado_em: Optional[str] = None
    erro_msg: Optional[str] = None
    tentativas_publicacao: int = 0
    criado_em: str


class VideoDetailResponse(VideoResponse):
    app_nome: Optional[str] = None
    conteudo: Optional[ConteudoResponse] = None