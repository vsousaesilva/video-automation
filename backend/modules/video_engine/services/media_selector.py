import logging
import os

from core.db import get_supabase
from modules.video_engine.services.pexels import search_pexels_videos, clear_download_cache
from modules.video_engine.services.tts import ensure_pipeline_dir

logger = logging.getLogger(__name__)


def _tag_match_score(asset_tags: list | None, keywords: list[str]) -> int:
    """Calcula score de relevancia: quantidade de tags que casam com as keywords."""
    if not asset_tags:
        return 0
    asset_tags_lower = {t.lower() for t in asset_tags}
    keywords_lower = {k.lower() for k in keywords}
    return len(asset_tags_lower & keywords_lower)


def _fetch_assets(query_builder) -> list[dict]:
    """Executa query e retorna dados."""
    result = query_builder.eq("ativo", True).execute()
    return result.data or []


async def select_media_for_script(
    negocio_id: str,
    workspace_id: str,
    visual_keywords: list[str],
    min_count: int = 3,
    orientation: str = "portrait",
    video_id: str | None = None,
) -> list[str]:
    """
    Seleciona midia para uso no video seguindo a hierarquia:
      1. Banco de imagens do app (match por tags)
      2. Banco de imagens do workspace (fallback)
      3. Pexels API (fallback final, com download local)

    Args:
        negocio_id: ID do negócio
        workspace_id: ID do workspace
        visual_keywords: palavras-chave para busca de midia
        min_count: minimo de midias a retornar (padrao 3)
        orientation: "portrait" (9:16) ou "landscape" (16:9)
        video_id: ID do video para organizar pasta temporaria

    Returns:
        Lista de URLs (banco local) ou caminhos locais (Pexels) de midia
    """
    supabase = get_supabase()
    selected: list[str] = []

    logger.info(
        f"Selecionando midia para negocio={negocio_id}, "
        f"keywords={visual_keywords}, min={min_count}"
    )

    # 1. Buscar assets do app
    app_assets = _fetch_assets(
        supabase.table("media_assets")
        .select("url_storage, tags")
        .eq("negocio_id", negocio_id)
    )

    scored = [
        (asset, _tag_match_score(asset.get("tags"), visual_keywords))
        for asset in app_assets
    ]
    scored.sort(key=lambda x: x[1], reverse=True)

    for asset, score in scored:
        if len(selected) >= min_count:
            break
        selected.append(asset["url_storage"])

    logger.info(f"Banco do negócio: {len(selected)} midias encontradas")

    # 2. Se ainda falta, buscar assets globais do workspace
    if len(selected) < min_count:
        workspace_assets = _fetch_assets(
            supabase.table("media_assets")
            .select("url_storage, tags")
            .eq("workspace_id", workspace_id)
            .is_("negocio_id", "null")
        )

        scored_ws = [
            (asset, _tag_match_score(asset.get("tags"), visual_keywords))
            for asset in workspace_assets
        ]
        scored_ws.sort(key=lambda x: x[1], reverse=True)

        for asset, score in scored_ws:
            if len(selected) >= min_count:
                break
            if asset["url_storage"] not in selected:
                selected.append(asset["url_storage"])

        logger.info(f"Banco do workspace: total acumulado {len(selected)} midias")

    # 3. Fallback Pexels (download local)
    if len(selected) < min_count:
        remaining = min_count - len(selected)
        logger.info(f"Buscando {remaining} midias no Pexels como fallback")

        download_dir = None
        if video_id:
            download_dir = os.path.join(ensure_pipeline_dir(video_id), "media")

        pexels_paths = await search_pexels_videos(
            visual_keywords,
            count=remaining,
            orientation=orientation,
            download_dir=download_dir,
        )
        selected.extend(pexels_paths)
        logger.info(f"Pexels: +{len(pexels_paths)} midias. Total final: {len(selected)}")

    return selected
