import hashlib
import logging
import os
from urllib.parse import urlparse

import httpx

from config import get_settings
from services.tts import PIPELINE_TMP_DIR

logger = logging.getLogger(__name__)

# Cache em memoria: mapeia URL original -> caminho local baixado
_download_cache: dict[str, str] = {}


def clear_download_cache() -> None:
    """Limpa o cache de downloads (chamar entre execucoes do pipeline)."""
    _download_cache.clear()


def _url_to_filename(url: str, ext: str = ".mp4") -> str:
    """Gera nome de arquivo determinístico a partir da URL."""
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"pexels_{url_hash}{ext}"


async def _download_file(url: str, dest_dir: str, ext: str = ".mp4") -> str:
    """Baixa arquivo da URL para o diretorio destino. Usa cache."""
    if url in _download_cache and os.path.exists(_download_cache[url]):
        logger.info(f"Cache hit: {_download_cache[url]}")
        return _download_cache[url]

    filename = _url_to_filename(url, ext)
    dest_path = os.path.join(dest_dir, filename)

    # Se ja existe no disco (de execucao anterior na mesma pasta)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
        _download_cache[url] = dest_path
        return dest_path

    logger.info(f"Baixando midia Pexels: {url[:80]}...")

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(url, timeout=60)
        resp.raise_for_status()

        with open(dest_path, "wb") as f:
            f.write(resp.content)

    _download_cache[url] = dest_path
    logger.info(f"Download concluido: {dest_path} ({os.path.getsize(dest_path)} bytes)")
    return dest_path


async def search_videos(
    keywords: list[str],
    count: int = 5,
    orientation: str = "portrait",
    download_dir: str | None = None,
) -> list[str]:
    """
    Busca videos no Pexels por palavras-chave, baixa para pasta local.

    Args:
        keywords: termos de busca
        count: quantidade desejada de clipes
        orientation: "portrait" (9:16) ou "landscape" (16:9)
        download_dir: pasta para salvar os clipes. Se None, usa tmp.

    Returns:
        Lista de caminhos locais dos arquivos baixados
    """
    settings = get_settings()
    if not settings.pexels_api_key:
        logger.warning("PEXELS_API_KEY nao configurada, retornando lista vazia")
        return []

    query = " ".join(keywords[:5])
    pexels_orientation = "portrait" if orientation == "portrait" else "landscape"

    if download_dir is None:
        download_dir = os.path.join(PIPELINE_TMP_DIR, "pexels_cache")
    os.makedirs(download_dir, exist_ok=True)

    video_urls: list[str] = []
    local_paths: list[str] = []

    headers = {"Authorization": settings.pexels_api_key}

    async with httpx.AsyncClient() as client:
        # Busca videos
        resp = await client.get(
            "https://api.pexels.com/videos/search",
            params={
                "query": query,
                "per_page": count,
                "orientation": pexels_orientation,
            },
            headers=headers,
            timeout=15,
        )

        if resp.status_code == 200:
            data = resp.json()
            for video in data.get("videos", []):
                files = video.get("video_files", [])
                # Prioriza HD
                hd = [f for f in files if f.get("quality") == "hd"]
                chosen = hd[0] if hd else (files[0] if files else None)
                if chosen and chosen.get("link"):
                    video_urls.append(chosen["link"])

        # Se nao encontrou videos suficientes, busca imagens
        if len(video_urls) < count:
            remaining = count - len(video_urls)
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query": query,
                    "per_page": remaining,
                    "orientation": pexels_orientation,
                },
                headers=headers,
                timeout=15,
            )

            if resp.status_code == 200:
                data = resp.json()
                for photo in data.get("photos", []):
                    src = photo.get("src", {})
                    url = src.get("large2x") or src.get("original", "")
                    if url:
                        video_urls.append(url)

    # Baixar cada midia para pasta local
    for url in video_urls[:count]:
        try:
            # Detecta extensao pela URL
            parsed = urlparse(url)
            path = parsed.path.lower()
            if path.endswith(".jpg") or path.endswith(".jpeg"):
                ext = ".jpg"
            elif path.endswith(".png"):
                ext = ".png"
            elif path.endswith(".webp"):
                ext = ".webp"
            else:
                ext = ".mp4"

            local_path = await _download_file(url, download_dir, ext)
            local_paths.append(local_path)
        except Exception as e:
            logger.error(f"Erro ao baixar midia Pexels: {e}")

    return local_paths


# Mantém compatibilidade com media_selector existente
async def search_pexels_videos(
    keywords: list[str],
    count: int = 5,
    orientation: str = "portrait",
    download_dir: str | None = None,
) -> list[str]:
    """Alias para search_videos, mantendo compatibilidade."""
    return await search_videos(keywords, count, orientation, download_dir)