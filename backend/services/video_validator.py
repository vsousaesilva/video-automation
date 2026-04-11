"""
Validação automática de vídeos gerados pelo pipeline.
Sessão 10 — checks de duração, tamanho, áudio e resolução.
"""

import logging
import os
from dataclasses import dataclass, field

from mutagen.mp4 import MP4

from db import get_supabase
from services.video_builder import (
    V_WIDTH, V_HEIGHT, V_MIN_DURATION, V_MAX_DURATION,
    H_WIDTH, H_HEIGHT, H_MIN_DURATION, H_MAX_DURATION,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool = True
    errors: list[str] = field(default_factory=list)


def _check_file_size(path: str, label: str, min_bytes: int = 1_048_576) -> list[str]:
    """Verifica se o arquivo tem pelo menos min_bytes (padrão 1 MB)."""
    errors = []
    if not os.path.exists(path):
        errors.append(f"{label}: arquivo não encontrado em {path}")
        return errors
    size = os.path.getsize(path)
    if size < min_bytes:
        errors.append(f"{label}: tamanho {size} bytes é menor que o mínimo de {min_bytes} bytes")
    return errors


def _check_duration(path: str, label: str, min_sec: int, max_sec: int) -> list[str]:
    """Verifica se a duração do vídeo está dentro do range esperado."""
    errors = []
    try:
        mp4 = MP4(path)
        duration = mp4.info.length
        if duration < min_sec:
            errors.append(f"{label}: duração {duration:.1f}s é menor que o mínimo de {min_sec}s")
        if duration > max_sec:
            errors.append(f"{label}: duração {duration:.1f}s excede o máximo de {max_sec}s")
    except Exception as e:
        errors.append(f"{label}: erro ao ler duração — {e}")
    return errors


def _check_audio(path: str, label: str) -> list[str]:
    """Verifica se o vídeo contém faixa de áudio."""
    errors = []
    try:
        mp4 = MP4(path)
        if mp4.info.length <= 0:
            errors.append(f"{label}: arquivo MP4 inválido (duração zero)")
            return errors
        # MP4 sem áudio geralmente não tem codec de áudio
        if not getattr(mp4.info, "channels", None) or mp4.info.channels == 0:
            errors.append(f"{label}: nenhuma faixa de áudio detectada")
    except Exception as e:
        errors.append(f"{label}: erro ao verificar áudio — {e}")
    return errors


def _check_resolution(path: str, label: str, expected_w: int, expected_h: int) -> list[str]:
    """Verifica se a resolução do vídeo corresponde ao esperado via MoviePy."""
    errors = []
    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(path)
        w, h = clip.size
        clip.close()
        if w != expected_w or h != expected_h:
            errors.append(
                f"{label}: resolução {w}x{h} difere da esperada {expected_w}x{expected_h}"
            )
    except Exception as e:
        errors.append(f"{label}: erro ao verificar resolução — {e}")
    return errors


def validate_video(video: dict, app: dict) -> ValidationResult:
    """
    Valida um vídeo gerado pelo pipeline.

    Args:
        video: registro da tabela videos (dict do Supabase)
        app: registro da tabela apps (dict do Supabase)

    Returns:
        ValidationResult com is_valid e lista de errors
    """
    result = ValidationResult()

    vertical_path = video.get("url_storage_vertical")
    horizontal_path = video.get("url_storage_horizontal")

    formatos_youtube = app.get("formato_youtube")
    plataformas = app.get("plataformas", [])
    gera_vertical = "instagram" in plataformas or formatos_youtube in ("9_16", "ambos")
    gera_horizontal = formatos_youtube in ("16_9", "ambos")

    # --- Validar vertical ---
    if gera_vertical and vertical_path:
        if os.path.exists(vertical_path):
            result.errors.extend(_check_file_size(vertical_path, "Vertical"))
            result.errors.extend(
                _check_duration(vertical_path, "Vertical", V_MIN_DURATION, V_MAX_DURATION)
            )
            result.errors.extend(_check_audio(vertical_path, "Vertical"))
            result.errors.extend(
                _check_resolution(vertical_path, "Vertical", V_WIDTH, V_HEIGHT)
            )
        else:
            result.errors.append(f"Vertical: arquivo não encontrado em {vertical_path}")
    elif gera_vertical and not vertical_path:
        result.errors.append("Vertical: vídeo vertical esperado mas não foi gerado")

    # --- Validar horizontal ---
    if gera_horizontal and horizontal_path:
        if os.path.exists(horizontal_path):
            result.errors.extend(_check_file_size(horizontal_path, "Horizontal"))
            result.errors.extend(
                _check_duration(horizontal_path, "Horizontal", H_MIN_DURATION, H_MAX_DURATION)
            )
            result.errors.extend(_check_audio(horizontal_path, "Horizontal"))
            result.errors.extend(
                _check_resolution(horizontal_path, "Horizontal", H_WIDTH, H_HEIGHT)
            )
        else:
            result.errors.append(f"Horizontal: arquivo não encontrado em {horizontal_path}")
    elif gera_horizontal and not horizontal_path:
        result.errors.append("Horizontal: vídeo horizontal esperado mas não foi gerado")

    if result.errors:
        result.is_valid = False

    return result


def update_video_status_error(video_id: str, errors: list[str]) -> None:
    """Atualiza o vídeo para status erro_validacao e salva as mensagens de erro."""
    supabase = get_supabase()
    erro_msg = "; ".join(errors)
    supabase.table("videos").update({
        "status": "erro_validacao",
        "erro_msg": erro_msg,
    }).eq("id", video_id).execute()
    logger.warning(f"Vídeo {video_id} falhou na validação: {erro_msg}")


def update_video_status_approved(video_id: str) -> None:
    """Atualiza o vídeo para status aguardando_aprovacao após validação bem-sucedida."""
    supabase = get_supabase()
    supabase.table("videos").update({
        "status": "aguardando_aprovacao",
    }).eq("id", video_id).execute()
    logger.info(f"Vídeo {video_id} validado com sucesso — aguardando aprovação")


def _log_etapa(app_id: str | None, video_id: str | None, etapa: str, status: str, mensagem: str):
    """Registra log de etapa no banco."""
    try:
        supabase = get_supabase()
        supabase.table("execution_logs").insert({
            "app_id": app_id,
            "video_id": video_id,
            "etapa": etapa,
            "status": status,
            "mensagem": mensagem,
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao registrar log: {e}")