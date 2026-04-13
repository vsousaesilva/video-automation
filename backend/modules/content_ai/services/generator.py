"""
Content AI Generator — integração Gemini com prompts especializados por tipo de conteúdo.
"""

import json
import logging
from datetime import datetime, timezone

import google.generativeai as genai

from core.config import get_settings
from core.db import get_supabase

logger = logging.getLogger(__name__)

MAX_RETRIES = 3

# === Prompts especializados por tipo ===

SYSTEM_PROMPTS = {
    "copy_ads": """Você é um copywriter especialista em anúncios digitais (Meta Ads, Google Ads, TikTok Ads).
Crie textos persuasivos, curtos e com CTAs claros. Use gatilhos mentais (urgência, escassez, prova social).
Adapte o formato para a plataforma especificada.""",

    "legenda": """Você é um social media manager especialista em legendas para redes sociais.
Crie legendas envolventes, com emojis estratégicos e hashtags relevantes.
Adapte o tom e tamanho para a plataforma (Instagram: até 2200 chars, LinkedIn: até 3000 chars).""",

    "roteiro": """Você é um roteirista especialista em vídeos curtos de marketing digital.
Crie roteiros narrados para vídeos de 30-90 segundos. O texto deve ser fluído para TTS (text-to-speech).
Inclua gancho nos primeiros 3 segundos, desenvolvimento e CTA no final.""",

    "artigo": """Você é um redator SEO especialista em artigos de blog.
Crie artigos bem estruturados com H2/H3, parágrafos curtos, listas quando apropriado.
Otimize para SEO com palavras-chave naturais no texto.""",

    "resposta_comentario": """Você é um community manager especialista em atendimento em redes sociais.
Crie respostas empáticas, profissionais e que resolvam a dúvida/reclamação.
Mantenha o tom da marca e ofereça soluções concretas.""",

    "email_marketing": """Você é um especialista em email marketing com altas taxas de conversão.
Crie emails com subject lines atrativas, corpo persuasivo e CTA claro.
Use personalização, escaneabilidade (parágrafos curtos, bullets) e senso de urgência quando apropriado.""",
}

OUTPUT_FORMATS = {
    "copy_ads": {
        "titulo": "headline principal do anúncio",
        "conteudo": "corpo do anúncio (texto principal)",
        "variacao_titulo": "headline alternativa",
        "variacao_conteudo": "corpo alternativo",
        "cta": "texto do botão CTA",
    },
    "legenda": {
        "titulo": "primeira linha (gancho)",
        "conteudo": "legenda completa com emojis",
        "hashtags": ["lista", "de", "hashtags"],
    },
    "roteiro": {
        "titulo": "título do vídeo",
        "conteudo": "roteiro narrado completo (texto para TTS)",
        "gancho": "primeiros 3 segundos (hook)",
        "cta": "chamada para ação final",
        "duracao_estimada_segundos": 60,
    },
    "artigo": {
        "titulo": "título SEO do artigo",
        "conteudo": "artigo completo em markdown",
        "meta_description": "meta description para SEO (até 160 chars)",
        "keywords": ["palavras", "chave", "seo"],
    },
    "resposta_comentario": {
        "titulo": "resumo da resposta",
        "conteudo": "resposta completa ao comentário",
    },
    "email_marketing": {
        "titulo": "subject line do email",
        "conteudo": "corpo do email em HTML simples",
        "preview_text": "texto de preview (até 90 chars)",
        "cta": "texto do botão CTA",
    },
}


def _build_prompt(
    tipo: str,
    tom_voz: str,
    idioma: str,
    contexto: dict,
    prompt_usuario: str | None,
    plataforma: str | None,
    template_prompt: str | None = None,
) -> tuple[str, str]:
    """Monta system prompt e user prompt para o Gemini."""

    system = SYSTEM_PROMPTS.get(tipo, SYSTEM_PROMPTS["copy_ads"])
    output_format = OUTPUT_FORMATS.get(tipo, OUTPUT_FORMATS["copy_ads"])

    # Contexto do negócio (se disponível)
    negocio_ctx = ""
    if contexto:
        negocio_nome = contexto.get("negocio_nome", "")
        if negocio_nome:
            negocio_ctx = f"""
=== DADOS DO NEGÓCIO ===
Nome: {negocio_nome}
Categoria: {contexto.get("categoria", "")}
Descrição: {contexto.get("descricao", "")}
Público-alvo: {contexto.get("publico_alvo", "")}
CTA principal: {contexto.get("cta", "")}
"""

    plataforma_ctx = f"\nPlataforma alvo: {plataforma}" if plataforma else ""

    if template_prompt:
        # Substituir variáveis do template
        user_prompt = template_prompt
        for key, value in contexto.items():
            user_prompt = user_prompt.replace(f"{{{{{key}}}}}", str(value))
    else:
        user_prompt = f"""Gere conteúdo do tipo "{tipo}" com as seguintes especificações:

Tom de voz: {tom_voz}
Idioma: {idioma}{plataforma_ctx}
{negocio_ctx}
"""
        if prompt_usuario:
            user_prompt += f"\nInstruções adicionais do usuário:\n{prompt_usuario}\n"

    user_prompt += f"""
=== FORMATO DE RESPOSTA ===
Responda EXCLUSIVAMENTE com um JSON válido, sem markdown, sem blocos de código:
{json.dumps(output_format, ensure_ascii=False, indent=2)}

Substitua os valores de exemplo pelo conteúdo real gerado."""

    return system, user_prompt


def _parse_response(text: str) -> dict:
    """Extrai JSON da resposta do Gemini."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


async def generate_content(
    workspace_id: str,
    user_id: str,
    tipo: str,
    tom_voz: str = "profissional",
    idioma: str = "pt-BR",
    negocio_id: str | None = None,
    template_id: str | None = None,
    prompt_usuario: str | None = None,
    contexto: dict | None = None,
    quantidade: int = 1,
    plataforma: str | None = None,
) -> dict:
    """
    Gera conteúdo via Gemini e salva no banco.

    Returns:
        dict com request_id, status e lista de contents gerados
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY não configurada")

    supabase = get_supabase()
    contexto = contexto or {}

    # Buscar dados do negócio se fornecido
    if negocio_id and "negocio_nome" not in contexto:
        neg = supabase.table("negocios").select("*").eq("id", negocio_id).single().execute()
        if neg.data:
            contexto.update({
                "negocio_nome": neg.data.get("nome", ""),
                "categoria": neg.data.get("categoria", ""),
                "descricao": neg.data.get("descricao", ""),
                "publico_alvo": neg.data.get("publico_alvo", ""),
                "cta": neg.data.get("cta", ""),
                "funcionalidades": neg.data.get("funcionalidades", []),
                "diferenciais": neg.data.get("diferenciais", []),
            })

    # Buscar template se fornecido
    template_prompt = None
    if template_id:
        tpl = supabase.table("content_templates").select("*").eq("id", template_id).single().execute()
        if tpl.data:
            template_prompt = tpl.data.get("prompt_template")
            if not tom_voz and tpl.data.get("tom_voz"):
                tom_voz = tpl.data["tom_voz"]

    # Criar request no banco
    request_data = {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "template_id": template_id,
        "negocio_id": negocio_id,
        "tipo": tipo,
        "tom_voz": tom_voz,
        "idioma": idioma,
        "prompt_usuario": prompt_usuario,
        "contexto": contexto,
        "quantidade": quantidade,
        "status": "processing",
    }
    req_result = supabase.table("content_requests").insert(request_data).execute()
    request_id = req_result.data[0]["id"]

    # Configurar Gemini
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    system_prompt, user_prompt = _build_prompt(
        tipo, tom_voz, idioma, contexto, prompt_usuario, plataforma, template_prompt
    )

    generated = []
    for i in range(quantidade):
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = model.generate_content(
                    [
                        {"role": "user", "parts": [{"text": system_prompt + "\n\n" + user_prompt}]},
                    ],
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.85 + (i * 0.05),  # variar temperatura entre variações
                        max_output_tokens=4096,
                    ),
                )

                parsed = _parse_response(response.text)
                titulo = parsed.get("titulo", "")
                conteudo = parsed.get("conteudo", "")

                if not conteudo:
                    last_error = ValueError("Conteúdo vazio na resposta")
                    continue

                # Salvar conteúdo gerado
                gen_data = {
                    "request_id": request_id,
                    "workspace_id": workspace_id,
                    "negocio_id": negocio_id,
                    "tipo": tipo,
                    "titulo": titulo,
                    "conteudo": conteudo,
                    "metadata": {k: v for k, v in parsed.items() if k not in ("titulo", "conteudo")},
                    "tokens_usados": getattr(response, "usage_metadata", None) and response.usage_metadata.total_token_count or 0,
                }
                gen_result = supabase.table("generated_contents").insert(gen_data).execute()
                generated.append(gen_result.data[0])
                break

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error attempt {attempt}/{MAX_RETRIES}: {e}")
                last_error = e
            except Exception as e:
                logger.warning(f"Generation error attempt {attempt}/{MAX_RETRIES}: {e}")
                last_error = e

        if last_error and len(generated) <= i:
            logger.error(f"Failed to generate variation {i+1}: {last_error}")

    # Atualizar status do request
    final_status = "completed" if generated else "failed"
    update = {"status": final_status}
    if not generated and last_error:
        update["erro_msg"] = str(last_error)
    supabase.table("content_requests").update(update).eq("id", request_id).execute()

    # Incrementar uso (conteudos_gerados)
    try:
        from core.billing import increment_usage
        for _ in generated:
            increment_usage(workspace_id, "conteudos_gerados")
    except Exception as e:
        logger.warning(f"Erro ao incrementar uso: {e}")

    return {
        "request_id": request_id,
        "status": final_status,
        "contents": generated,
    }
