import uuid
from pathlib import PurePosixPath

from core.db import get_supabase
from core.config import get_settings

BUCKET_NAME = "media-bank"

ALLOWED_EXTENSIONS = {
    "imagem": {"jpg", "jpeg", "png", "webp"},
    "video": {"mp4"},
}

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "video/mp4",
}

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


def detect_tipo(content_type: str) -> str:
    if content_type.startswith("image/"):
        return "imagem"
    if content_type.startswith("video/"):
        return "video"
    raise ValueError(f"Tipo de arquivo nao suportado: {content_type}")


def validate_file(filename: str, content_type: str, size: int) -> str:
    """Valida arquivo e retorna o tipo (imagem/video). Levanta ValueError se invalido."""
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(
            f"Tipo de arquivo nao aceito: {content_type}. "
            f"Aceitos: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
        )

    if size > MAX_FILE_SIZE:
        raise ValueError(
            f"Arquivo excede o limite de {MAX_FILE_SIZE // (1024*1024)}MB"
        )

    ext = PurePosixPath(filename).suffix.lstrip(".").lower()
    tipo = detect_tipo(content_type)

    if ext not in ALLOWED_EXTENSIONS.get(tipo, set()):
        raise ValueError(
            f"Extensao '.{ext}' nao aceita para tipo '{tipo}'. "
            f"Aceitas: {', '.join(sorted(ALLOWED_EXTENSIONS[tipo]))}"
        )

    return tipo


def build_storage_path(workspace_id: str, app_id: str | None, filename: str) -> str:
    """Gera caminho unico no Storage: workspace_id/[app_id/]uuid_filename"""
    unique_name = f"{uuid.uuid4().hex}_{filename}"
    if app_id:
        return f"{workspace_id}/{app_id}/{unique_name}"
    return f"{workspace_id}/global/{unique_name}"


async def upload_to_storage(file_bytes: bytes, path: str, content_type: str) -> str:
    """Faz upload para o Supabase Storage e retorna a URL publica."""
    supabase = get_supabase()
    supabase.storage.from_(BUCKET_NAME).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type},
    )

    settings = get_settings()
    public_url = f"{settings.supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{path}"
    return public_url


async def delete_from_storage(url_storage: str) -> None:
    """Remove arquivo do Supabase Storage a partir da URL."""
    # Extrai o path relativo ao bucket da URL
    marker = f"/storage/v1/object/public/{BUCKET_NAME}/"
    idx = url_storage.find(marker)
    if idx == -1:
        return
    path = url_storage[idx + len(marker):]

    supabase = get_supabase()
    supabase.storage.from_(BUCKET_NAME).remove([path])
