"""
Content AI — endpoints de geração de conteúdo com IA.
POST   /content-ai/generate       — gerar conteúdo
GET    /content-ai/history         — histórico de gerações
GET    /content-ai/history/{id}    — detalhes de uma geração
GET    /content-ai/templates       — templates disponíveis
POST   /content-ai/templates       — criar template customizado
PUT    /content-ai/templates/{id}  — atualizar template
DELETE /content-ai/templates/{id}  — remover template
POST   /content-ai/rate/{id}       — avaliar conteúdo gerado
POST   /content-ai/use-in-video    — enviar conteúdo para o Video Engine
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import get_current_user
from core.db import get_supabase
from modules.content_ai.schemas import (
    GenerateContentRequest,
    TemplateCreateRequest,
    TemplateUpdateRequest,
    RateContentRequest,
    UseInVideoEngineRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/content-ai", tags=["Content AI"])


def _find_one(table_query):
    """Executa query com .limit(1) e retorna o primeiro resultado ou None."""
    result = table_query.limit(1).execute()
    return result.data[0] if result.data else None


# ============================================================
# Geração de conteúdo
# ============================================================

@router.post("/generate")
async def generate_content(
    body: GenerateContentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Gera conteúdo com IA (copy, legenda, roteiro, artigo, etc.)."""
    from modules.content_ai.services.generator import generate_content as gen

    try:
        result = await gen(
            workspace_id=current_user["workspace_id"],
            user_id=current_user["id"],
            tipo=body.tipo.value,
            tom_voz=body.tom_voz.value,
            idioma=body.idioma,
            negocio_id=body.negocio_id,
            template_id=body.template_id,
            prompt_usuario=body.prompt_usuario,
            contexto=body.contexto,
            quantidade=body.quantidade,
            plataforma=body.plataforma,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar conteúdo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar conteúdo: {str(e)}")


# ============================================================
# Diagnóstico — status do pipeline de vídeo
# ============================================================

@router.get("/pipeline-status")
async def pipeline_status(
    current_user: dict = Depends(get_current_user),
):
    """Mostra conteúdos em pipeline (gerado, processando_video, erro) com diagnóstico."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    # Buscar todos negócios do workspace
    negs = supabase.table("negocios").select("id, nome").eq("workspace_id", workspace_id).execute()
    neg_ids = [n["id"] for n in (negs.data or [])]
    neg_names = {n["id"]: n["nome"] for n in (negs.data or [])}

    if not neg_ids:
        return {"items": [], "diagnostico": "Nenhum negocio encontrado"}

    # Buscar conteúdos em pipeline
    conteudos = (
        supabase.table("conteudos")
        .select("*")
        .in_("negocio_id", neg_ids)
        .in_("status", ["gerado", "processando_video", "erro"])
        .order("criado_em", desc=True)
        .limit(20)
        .execute()
    )

    items = []
    for c in (conteudos.data or []):
        items.append({
            "id": c["id"],
            "negocio": neg_names.get(c["negocio_id"], c["negocio_id"]),
            "titulo": c.get("titulo"),
            "tipo": c.get("tipo_conteudo"),
            "status": c["status"],
            "erro": c.get("erro_msg"),
            "criado_em": c.get("criado_em"),
        })

    # Checar Redis
    try:
        from modules.video_engine.routers.pipeline import _celery_available
        redis_ok = _celery_available()
    except Exception:
        redis_ok = False

    return {
        "items": items,
        "redis_disponivel": redis_ok,
        "total_em_pipeline": len(items),
    }


# ============================================================
# Histórico
# ============================================================

@router.get("/history")
async def list_history(
    tipo: str | None = Query(None),
    negocio_id: str | None = Query(None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
):
    """Lista histórico de gerações do workspace."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("content_requests")
        .select("*, generated_contents(*)")
        .eq("workspace_id", workspace_id)
        .order("criado_em", desc=True)
        .range(offset, offset + limit - 1)
    )
    if tipo:
        query = query.eq("tipo", tipo)
    if negocio_id:
        query = query.eq("negocio_id", negocio_id)

    result = query.execute()
    return {"items": result.data, "count": len(result.data)}


@router.get("/history/{request_id}")
async def get_history_detail(
    request_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Detalhes de uma geração específica."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    item = _find_one(
        supabase.table("content_requests")
        .select("*, generated_contents(*)")
        .eq("id", request_id)
        .eq("workspace_id", workspace_id)
    )
    if not item:
        raise HTTPException(status_code=404, detail="Geração não encontrada")
    return item


# ============================================================
# Templates
# ============================================================

@router.get("/templates")
async def list_templates(
    tipo: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Lista templates de conteúdo do workspace."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    query = (
        supabase.table("content_templates")
        .select("*")
        .eq("workspace_id", workspace_id)
        .eq("ativo", True)
        .order("criado_em", desc=True)
    )
    if tipo:
        query = query.eq("tipo", tipo)

    result = query.execute()
    return {"items": result.data}


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Cria um template customizado de conteúdo."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    data = {
        "workspace_id": workspace_id,
        "nome": body.nome,
        "tipo": body.tipo.value,
        "tom_voz": body.tom_voz,
        "idioma": body.idioma,
        "prompt_sistema": body.prompt_sistema,
        "prompt_template": body.prompt_template,
        "variaveis": body.variaveis or [],
    }
    result = supabase.table("content_templates").insert(data).execute()
    return result.data[0]


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    body: TemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Atualiza um template existente."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = _find_one(
        supabase.table("content_templates")
        .select("id")
        .eq("id", template_id)
        .eq("workspace_id", workspace_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    update_data = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    update_data["atualizado_em"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("content_templates")
        .update(update_data)
        .eq("id", template_id)
        .execute()
    )
    return result.data[0]


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove (soft-delete) um template."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = _find_one(
        supabase.table("content_templates")
        .select("id")
        .eq("id", template_id)
        .eq("workspace_id", workspace_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Template não encontrado")

    supabase.table("content_templates").update({"ativo": False}).eq("id", template_id).execute()
    return {"status": "deleted"}


# ============================================================
# Avaliação e integração
# ============================================================

@router.post("/rate/{content_id}")
async def rate_content(
    content_id: str,
    body: RateContentRequest,
    current_user: dict = Depends(get_current_user),
):
    """Avalia um conteúdo gerado (1-5 estrelas)."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    existing = _find_one(
        supabase.table("generated_contents")
        .select("id")
        .eq("id", content_id)
        .eq("workspace_id", workspace_id)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    supabase.table("generated_contents").update({"avaliacao": body.avaliacao}).eq("id", content_id).execute()
    return {"status": "rated", "avaliacao": body.avaliacao}


@router.post("/use-in-video")
async def use_in_video_engine(
    body: UseInVideoEngineRequest,
    current_user: dict = Depends(get_current_user),
):
    """Envia conteúdo gerado para o Video Engine como conteúdo de um negócio."""
    supabase = get_supabase()
    workspace_id = current_user["workspace_id"]

    try:
        # Buscar conteúdo gerado
        content = _find_one(
            supabase.table("generated_contents")
            .select("*")
            .eq("id", body.generated_content_id)
            .eq("workspace_id", workspace_id)
        )
        if not content:
            raise HTTPException(status_code=404, detail="Conteúdo gerado não encontrado")

        metadata = content.get("metadata") or {}

        # Verificar que o negócio pertence ao workspace
        neg = _find_one(
            supabase.table("negocios")
            .select("id")
            .eq("id", body.negocio_id)
            .eq("workspace_id", workspace_id)
        )
        if not neg:
            raise HTTPException(status_code=404, detail="Negócio não encontrado")

        # Mapear tipo Content AI → enum tipo_conteudo do Video Engine
        # O enum Postgres aceita: problema_solucao, tutorial_rapido, beneficio_destaque,
        # prova_social, comparativo, curiosidade_nicho
        TIPO_MAP = {
            "roteiro": "tutorial_rapido",
            "copy_ads": "beneficio_destaque",
            "legenda": "beneficio_destaque",
            "artigo": "curiosidade_nicho",
            "resposta_comentario": "prova_social",
            "email_marketing": "problema_solucao",
        }
        tipo_video = TIPO_MAP.get(content.get("tipo", ""), "beneficio_destaque")

        # Criar conteúdo na tabela conteudos (Video Engine)
        conteudo_data = {
            "negocio_id": body.negocio_id,
            "tipo_conteudo": tipo_video,
            "roteiro": content.get("conteudo", ""),
            "titulo": content.get("titulo", ""),
            "descricao_youtube": metadata.get("meta_description", ""),
            "descricao_instagram": content.get("conteudo", "")[:2200],
            "hashtags_youtube": metadata.get("keywords", []),
            "hashtags_instagram": metadata.get("hashtags", []),
            "keywords_visuais": [],
            "keywords_seo": metadata.get("keywords", []),
            "status": "gerado",
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        result = supabase.table("conteudos").insert(conteudo_data).execute()

        # Marcar conteúdo como usado
        supabase.table("generated_contents").update({"usado_em": "video_engine"}).eq("id", body.generated_content_id).execute()

        conteudo_id = result.data[0]["id"]

        # Disparar construção do vídeo em background (Celery ou asyncio)
        try:
            from modules.video_engine.routers.pipeline import _celery_available
            if _celery_available():
                from modules.content_ai.tasks import build_video_from_content_task
                task = build_video_from_content_task.delay(conteudo_id, body.negocio_id, workspace_id)
                logger.info(f"Build video enfileirado via Celery: task_id={task.id}")
                return {
                    "status": "building",
                    "conteudo_id": conteudo_id,
                    "task_id": task.id,
                    "message": "Video sendo construido. Acompanhe em Aprovacoes.",
                }
            else:
                import asyncio
                from modules.video_engine.services.video_builder import build_all_formats

                neg_data = _find_one(
                    supabase.table("negocios").select("*").eq("id", body.negocio_id)
                )
                ws_data = _find_one(
                    supabase.table("workspaces").select("*").eq("id", workspace_id)
                )
                if neg_data and ws_data:
                    async def _build_with_error_handling():
                        try:
                            await build_all_formats(conteudo_id, neg_data, ws_data)
                        except Exception as e:
                            logger.error(f"Build video falhou (asyncio): {e}", exc_info=True)
                            try:
                                get_supabase().table("conteudos").update({
                                    "status": "erro",
                                    "erro_msg": str(e),
                                }).eq("id", conteudo_id).execute()
                            except Exception:
                                pass

                    asyncio.create_task(_build_with_error_handling())
                    logger.info(f"Build video disparado via asyncio (Redis indisponivel)")

                return {
                    "status": "building",
                    "conteudo_id": conteudo_id,
                    "message": "Video sendo construido. Acompanhe em Historico.",
                }
        except Exception as build_err:
            logger.warning(f"Não foi possível disparar build automaticamente: {build_err}")
            return {
                "status": "created",
                "conteudo_id": conteudo_id,
                "message": "Conteudo criado. O video será gerado na próxima execução do pipeline.",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao enviar para Video Engine: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao enviar para Video Engine: {str(e)}")
