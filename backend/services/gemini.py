import json
import logging
from datetime import datetime, timezone

import google.generativeai as genai
from httpx import TimeoutException

from config import get_settings
from db import get_supabase

logger = logging.getLogger(__name__)

TODOS_TIPOS = [
    "problema_solucao",
    "tutorial_rapido",
    "beneficio_destaque",
    "prova_social",
    "comparativo",
    "curiosidade_nicho",
]

DESCRICOES_TIPOS = {
    "problema_solucao": "Apresenta uma dor do usuário e como o app resolve",
    "tutorial_rapido": "Mostra como usar uma funcionalidade principal",
    "beneficio_destaque": "Foca em um diferencial específico do app",
    "prova_social": "Simula depoimento ou resultado de uso",
    "comparativo": "App vs. método tradicional",
    "curiosidade_nicho": "Dado ou fato do segmento + conexão com o app",
}

MAX_RETRIES = 3


def _escolher_tipo(last_7_types: list[str]) -> str:
    """Escolhe tipo de conteúdo evitando os últimos 7 usados."""
    disponiveis = [t for t in TODOS_TIPOS if t not in last_7_types]
    if not disponiveis:
        disponiveis = TODOS_TIPOS.copy()
    return disponiveis[0]


def _montar_prompt(app: dict, workspace: dict, tipo_escolhido: str) -> str:
    """Monta o prompt estruturado para o Gemini."""
    funcionalidades = app.get("funcionalidades") or []
    if isinstance(funcionalidades, list):
        funcionalidades_str = "\n".join(f"- {f}" for f in funcionalidades)
    else:
        funcionalidades_str = str(funcionalidades)

    diferenciais = app.get("diferenciais") or []
    if isinstance(diferenciais, list):
        diferenciais_str = "\n".join(f"- {d}" for d in diferenciais)
    else:
        diferenciais_str = str(diferenciais)

    keywords = app.get("keywords") or []
    if isinstance(keywords, list):
        keywords_str = ", ".join(keywords)
    else:
        keywords_str = str(keywords)

    tom_voz = app.get("tom_voz") or workspace.get("tom_voz") or "profissional"
    idioma = workspace.get("idioma") or "pt-BR"
    desc_tipo = DESCRICOES_TIPOS.get(tipo_escolhido, tipo_escolhido)

    return f"""Você é um especialista em marketing digital para aplicativos mobile.

Gere conteúdo completo para um vídeo de marketing do aplicativo descrito abaixo.

=== DADOS DO APLICATIVO ===
Nome: {app.get("nome", "")}
Categoria: {app.get("categoria", "")}
Descrição: {app.get("descricao", "")}
Público-alvo: {app.get("publico_alvo", "")}
Funcionalidades:
{funcionalidades_str}
Diferenciais:
{diferenciais_str}
CTA principal: {app.get("cta", "Baixe agora!")}
Link de download: {app.get("link_download", "")}
Palavras-chave SEO: {keywords_str}

=== CONFIGURAÇÃO ===
Tom de voz: {tom_voz}
Idioma: {idioma}
Tipo de conteúdo: {tipo_escolhido} — {desc_tipo}

=== INSTRUÇÕES ===
1. Crie um ROTEIRO NARRADO completo (texto que será convertido em áudio TTS). Duração alvo: 30 a 90 segundos de fala. Não inclua marcações de cena, apenas o texto narrado.
2. Crie um TÍTULO atrativo para o vídeo (máximo 100 caracteres).
3. Crie uma DESCRIÇÃO para YouTube (máximo 5000 caracteres), com parágrafos, links e CTA.
4. Crie uma DESCRIÇÃO para Instagram (máximo 2200 caracteres), mais concisa e com emojis.
5. Gere HASHTAGS para YouTube (15-20 tags relevantes).
6. Gere HASHTAGS para Instagram (20-30 tags relevantes).
7. Gere PALAVRAS-CHAVE VISUAIS (5-10 termos para busca de imagens/vídeos de stock que combinem com o roteiro).
8. Gere PALAVRAS-CHAVE SEO (10-15 termos para otimização de busca no YouTube).

=== FORMATO DE RESPOSTA ===
Responda EXCLUSIVAMENTE com um JSON válido, sem markdown, sem blocos de código, sem texto adicional:
{{
  "roteiro": "texto completo do roteiro narrado",
  "titulo": "título do vídeo",
  "descricao_youtube": "descrição completa para YouTube",
  "descricao_instagram": "descrição para Instagram",
  "hashtags_youtube": ["tag1", "tag2", ...],
  "hashtags_instagram": ["tag1", "tag2", ...],
  "keywords_visuais": ["keyword1", "keyword2", ...],
  "keywords_seo": ["keyword1", "keyword2", ...],
  "tipo_conteudo": "{tipo_escolhido}"
}}"""


def _parse_response(text: str) -> dict:
    """Extrai JSON da resposta do Gemini, tratando possíveis blocos de código."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # remove ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _validar_conteudo(data: dict) -> bool:
    """Valida se o JSON retornado tem todos os campos obrigatórios."""
    campos = [
        "roteiro", "titulo", "descricao_youtube", "descricao_instagram",
        "hashtags_youtube", "hashtags_instagram", "keywords_visuais",
        "keywords_seo", "tipo_conteudo",
    ]
    for campo in campos:
        if campo not in data or not data[campo]:
            return False
    if not isinstance(data["hashtags_youtube"], list):
        return False
    if not isinstance(data["hashtags_instagram"], list):
        return False
    if not isinstance(data["keywords_visuais"], list):
        return False
    if not isinstance(data["keywords_seo"], list):
        return False
    return True


def _log_etapa(app_id: str | None, etapa: str, status: str, mensagem: str, video_id: str | None = None):
    """Registra log de execução no banco."""
    supabase = get_supabase()
    log_data = {
        "etapa": etapa,
        "status": status,
        "mensagem": mensagem,
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }
    if app_id:
        log_data["app_id"] = app_id
    if video_id:
        log_data["video_id"] = video_id
    try:
        supabase.table("execution_logs").insert(log_data).execute()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")


async def generate_content(app: dict, workspace: dict, last_7_types: list[str]) -> dict:
    """
    Gera conteúdo completo via Gemini API.

    Args:
        app: dados do aplicativo (dict do banco)
        workspace: dados do workspace (dict do banco)
        last_7_types: lista dos últimos 7 tipos de conteúdo gerados

    Returns:
        dict com os campos do conteúdo gerado

    Raises:
        Exception se todas as tentativas falharem
    """
    settings = get_settings()

    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY não configurada")

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    tipo_escolhido = _escolher_tipo(last_7_types)
    prompt = _montar_prompt(app, workspace, tipo_escolhido)
    app_id = app["id"]

    _log_etapa(app_id, "gemini_inicio", "info",
               f"Iniciando geração de conteúdo. Tipo: {tipo_escolhido}")

    last_error = None
    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            _log_etapa(app_id, "gemini_chamada", "info",
                       f"Tentativa {tentativa}/{MAX_RETRIES}")

            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,
                    max_output_tokens=4096,
                ),
            )

            texto = response.text
            conteudo = _parse_response(texto)

            if not _validar_conteudo(conteudo):
                _log_etapa(app_id, "gemini_validacao", "erro",
                           f"Resposta inválida na tentativa {tentativa}")
                last_error = ValueError("Resposta do Gemini com campos ausentes ou inválidos")
                continue

            _log_etapa(app_id, "gemini_sucesso", "sucesso",
                       f"Conteúdo gerado com sucesso. Tipo: {conteudo['tipo_conteudo']}")

            return conteudo

        except json.JSONDecodeError as e:
            _log_etapa(app_id, "gemini_parse", "erro",
                       f"Erro de parse JSON na tentativa {tentativa}: {str(e)}")
            last_error = e
        except TimeoutException as e:
            _log_etapa(app_id, "gemini_timeout", "erro",
                       f"Timeout na tentativa {tentativa}: {str(e)}")
            last_error = e
        except Exception as e:
            _log_etapa(app_id, "gemini_erro", "erro",
                       f"Erro na tentativa {tentativa}: {str(e)}")
            last_error = e

    _log_etapa(app_id, "gemini_falha", "erro",
               f"Todas as {MAX_RETRIES} tentativas falharam. Último erro: {str(last_error)}")
    raise last_error or Exception("Falha na geração de conteúdo")


async def save_content(app_id: str, conteudo: dict) -> dict:
    """Salva o conteúdo gerado na tabela conteudos com status 'gerado'."""
    supabase = get_supabase()

    data = {
        "app_id": app_id,
        "tipo_conteudo": conteudo["tipo_conteudo"],
        "roteiro": conteudo["roteiro"],
        "titulo": conteudo["titulo"],
        "descricao_youtube": conteudo["descricao_youtube"],
        "descricao_instagram": conteudo["descricao_instagram"],
        "hashtags_youtube": conteudo["hashtags_youtube"],
        "hashtags_instagram": conteudo["hashtags_instagram"],
        "keywords_visuais": conteudo["keywords_visuais"],
        "keywords_seo": conteudo["keywords_seo"],
        "status": "gerado",
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }

    result = supabase.table("conteudos").insert(data).execute()

    _log_etapa(app_id, "conteudo_salvo", "sucesso",
               f"Conteúdo salvo com id={result.data[0]['id']}")

    return result.data[0]