"""Schemas Pydantic do modulo Benchmark (Sessao 10)."""
from pydantic import BaseModel, Field
from typing import Optional, Any
from enum import Enum


class RedeSocial(str, Enum):
    instagram = "instagram"
    youtube = "youtube"
    tiktok = "tiktok"
    website = "website"


class StatusReport(str, Enum):
    pendente = "pendente"
    processando = "processando"
    concluido = "concluido"
    erro = "erro"


# === Competitors ===

class CompetitorCreate(BaseModel):
    negocio_id: str = Field(min_length=1, description="Negocio ao qual o concorrente pertence")
    nome: str = Field(min_length=1, max_length=255)
    segmento: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    descricao: Optional[str] = None
    instagram_handle: Optional[str] = Field(None, max_length=100)
    youtube_handle: Optional[str] = Field(None, max_length=100)
    tiktok_handle: Optional[str] = Field(None, max_length=100)
    palavras_chave: list[str] = []


class CompetitorUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    segmento: Optional[str] = Field(None, max_length=100)
    website: Optional[str] = Field(None, max_length=500)
    descricao: Optional[str] = None
    instagram_handle: Optional[str] = Field(None, max_length=100)
    youtube_handle: Optional[str] = Field(None, max_length=100)
    tiktok_handle: Optional[str] = Field(None, max_length=100)
    palavras_chave: Optional[list[str]] = None
    ativo: Optional[bool] = None


# === Reports ===

class BenchmarkAnalyzeRequest(BaseModel):
    negocio_id: str = Field(min_length=1)
    nome: str = Field(min_length=1, max_length=255, description="Nome do relatorio")
    competitor_ids: list[str] = Field(min_length=1)
    redes: list[RedeSocial] = [RedeSocial.instagram, RedeSocial.youtube, RedeSocial.tiktok]
    incluir_keywords: bool = True
    incluir_insights: bool = True
    contexto_negocio: Optional[str] = Field(
        None, description="Descricao do negocio que contrata, para contextualizar insights"
    )


class ReportParams(BaseModel):
    redes: list[str] = []
    incluir_keywords: bool = True
    incluir_insights: bool = True
    contexto_negocio: Optional[str] = None
