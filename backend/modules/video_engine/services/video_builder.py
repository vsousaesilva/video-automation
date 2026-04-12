"""
Motor de montagem de video vertical (1080x1920) e horizontal (1920x1080).
Sessoes 8 e 9 — FFmpeg + MoviePy.
"""

import logging
import os
import textwrap
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx import CrossFadeIn
from PIL import Image

from modules.video_engine.services.tts import ensure_pipeline_dir

logger = logging.getLogger(__name__)

# Constantes compartilhadas
FPS = 30
FADE_DURATION = 0.3
CTA_DURATION = 5

# Formato vertical (Reels / Shorts)
V_WIDTH = 1080
V_HEIGHT = 1920
V_MIN_DURATION = 30
V_MAX_DURATION = 90

# Formato horizontal (YouTube)
H_WIDTH = 1920
H_HEIGHT = 1080
H_MIN_DURATION = 60
H_MAX_DURATION = 180

# Retrocompatibilidade — constantes usadas pelo build_vertical original
WIDTH = V_WIDTH
HEIGHT = V_HEIGHT
MIN_DURATION = V_MIN_DURATION
MAX_DURATION = V_MAX_DURATION

# Fonte padrao — caminho completo no Windows
_FONT_PATH = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf")
if not os.path.exists(_FONT_PATH):
    _FONT_PATH = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")


@dataclass
class VideoOutput:
    """Resultado da montagem de videos em um ou mais formatos."""
    vertical_path: Optional[str] = None
    horizontal_path: Optional[str] = None
    vertical_duration: Optional[float] = None
    horizontal_duration: Optional[float] = None
    vertical_url: Optional[str] = None
    horizontal_url: Optional[str] = None
    video_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers de log (Supabase)
# ---------------------------------------------------------------------------

def _log_etapa(
    app_id: str | None,
    video_id: str | None,
    etapa: str,
    status: str,
    mensagem: str,
):
    """Registra log de execucao no banco."""
    try:
        from core.db import get_supabase

        supabase = get_supabase()
        log_data = {
            "etapa": etapa,
            "status": status,
            "mensagem": mensagem,
            "criado_em": datetime.now(timezone.utc).isoformat(),
        }
        if app_id:
            log_data["negocio_id"] = app_id
        if video_id:
            log_data["video_id"] = video_id
        supabase.table("execution_logs").insert(log_data).execute()
    except Exception as e:
        logger.warning(f"Falha ao gravar log no banco: {e}")


# ---------------------------------------------------------------------------
# Preparacao de clipes
# ---------------------------------------------------------------------------

def _resize_and_crop_image(path: str, target_w: int, target_h: int) -> str:
    """Redimensiona e recorta imagem para a resolucao alvo com crop centralizado.
    Retorna caminho de arquivo temporario processado."""
    img = Image.open(path).convert("RGB")
    iw, ih = img.size
    target_ratio = target_w / target_h
    img_ratio = iw / ih

    if img_ratio > target_ratio:
        # Imagem mais larga: ajusta pela altura e corta laterais
        new_h = target_h
        new_w = int(iw * (target_h / ih))
    else:
        # Imagem mais alta: ajusta pela largura e corta topo/base
        new_w = target_w
        new_h = int(ih * (target_w / iw))

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Crop centralizado
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))

    out_path = path + "_resized.jpg"
    img.save(out_path, "JPEG", quality=95)
    return out_path


def _is_video_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".mp4", ".mov", ".avi", ".webm", ".mkv"}


def _make_clip(media_path: str, duration: float) -> VideoFileClip | ImageClip:
    """Cria um clipe (video ou imagem) com a duracao e resolucao alvo."""
    if _is_video_file(media_path):
        clip = VideoFileClip(media_path)
        # Redimensiona video mantendo aspect ratio e depois crop centralizado
        clip_ratio = clip.w / clip.h
        target_ratio = WIDTH / HEIGHT

        if clip_ratio > target_ratio:
            clip = clip.resized(height=HEIGHT)
        else:
            clip = clip.resized(width=WIDTH)

        # Crop centralizado
        clip = clip.cropped(
            x_center=clip.w / 2,
            y_center=clip.h / 2,
            width=WIDTH,
            height=HEIGHT,
        )

        # Ajusta duracao
        if clip.duration > duration:
            clip = clip.subclipped(0, duration)
        elif clip.duration < duration:
            clip = clip.looped(duration=duration)

        return clip
    else:
        # Imagem estatica
        resized_path = _resize_and_crop_image(media_path, WIDTH, HEIGHT)
        clip = ImageClip(resized_path).with_duration(duration)
        return clip


# ---------------------------------------------------------------------------
# Legendas
# ---------------------------------------------------------------------------

def _split_script_into_blocks(roteiro: str, words_per_block: int = 6) -> list[str]:
    """Divide o roteiro em blocos de N palavras para legendas."""
    words = roteiro.split()
    blocks = []
    for i in range(0, len(words), words_per_block):
        block = " ".join(words[i : i + words_per_block])
        blocks.append(block)
    return blocks


def _create_subtitle_clips(
    roteiro: str,
    total_duration: float,
) -> list[TextClip]:
    """Gera clipes de legenda sincronizados com a duracao total."""
    blocks = _split_script_into_blocks(roteiro, words_per_block=6)
    if not blocks:
        return []

    block_duration = total_duration / len(blocks)
    subtitle_clips = []

    for i, text in enumerate(blocks):
        start = i * block_duration
        # Quebra texto longo em 2 linhas
        wrapped = textwrap.fill(text, width=25)
        txt_clip = (
            TextClip(
                text=wrapped,
                font_size=48,
                color="white",
                font=_FONT_PATH,
                stroke_color="black",
                stroke_width=2,
                text_align="center",
                size=(WIDTH - 120, None),
            )
            .with_duration(block_duration)
            .with_start(start)
            .with_position(("center", HEIGHT - 400))
        )
        subtitle_clips.append(txt_clip)

    return subtitle_clips


# ---------------------------------------------------------------------------
# Marca d'agua (logo)
# ---------------------------------------------------------------------------

def _create_watermark(logo_path: str | None, total_duration: float) -> ImageClip | None:
    """Cria clipe de marca d'agua com 20% de opacidade no canto inferior direito."""
    if not logo_path or not os.path.exists(logo_path):
        return None

    logo_img = Image.open(logo_path).convert("RGBA")

    # Redimensiona logo para no maximo 120px de largura
    max_logo_w = 120
    ratio = max_logo_w / logo_img.width
    new_size = (max_logo_w, int(logo_img.height * ratio))
    logo_img = logo_img.resize(new_size, Image.LANCZOS)

    # Aplica 20% de opacidade
    alpha = logo_img.split()[3]
    alpha = alpha.point(lambda p: int(p * 0.2))
    logo_img.putalpha(alpha)

    tmp_path = logo_path + "_watermark.png"
    logo_img.save(tmp_path, "PNG")

    watermark = (
        ImageClip(tmp_path)
        .with_duration(total_duration)
        .with_position((WIDTH - new_size[0] - 30, HEIGHT - new_size[1] - 30))
    )
    return watermark


# ---------------------------------------------------------------------------
# CTA final
# ---------------------------------------------------------------------------

def _create_cta_clip(
    cta_text: str,
    cor_primaria: str,
    total_duration: float,
) -> TextClip:
    """Cria texto CTA nos ultimos 5 segundos do video."""
    cta_start = max(0, total_duration - CTA_DURATION)
    wrapped = textwrap.fill(cta_text, width=20)
    cta_clip = (
        TextClip(
            text=wrapped,
            font_size=56,
            color=cor_primaria or "#FFFFFF",
            font=_FONT_PATH,
            stroke_color="black",
            stroke_width=2,
            text_align="center",
            size=(WIDTH - 100, None),
        )
        .with_duration(CTA_DURATION)
        .with_start(cta_start)
        .with_position(("center", HEIGHT // 2 - 100))
        .with_effects([CrossFadeIn(0.5)])
    )
    return cta_clip


# ---------------------------------------------------------------------------
# Validacao de saida
# ---------------------------------------------------------------------------

def _validate_output(output_path: str, audio_duration: float) -> dict:
    """Valida o video gerado. Retorna dict com resultado."""
    errors = []

    if not os.path.exists(output_path):
        return {"valid": False, "errors": ["Arquivo de saida nao encontrado"]}

    file_size = os.path.getsize(output_path)
    if file_size < 1_000_000:  # < 1MB
        errors.append(f"Arquivo muito pequeno ({file_size} bytes), render pode ter falhado")

    # Verifica resolucao e duracao com MoviePy
    try:
        probe = VideoFileClip(output_path)
        w, h = probe.size
        dur = probe.duration

        if w != WIDTH or h != HEIGHT:
            errors.append(f"Resolucao incorreta: {w}x{h} (esperado {WIDTH}x{HEIGHT})")

        if dur < MIN_DURATION:
            errors.append(f"Duracao muito curta: {dur:.1f}s (minimo {MIN_DURATION}s)")
        elif dur > MAX_DURATION:
            errors.append(f"Duracao muito longa: {dur:.1f}s (maximo {MAX_DURATION}s)")

        if probe.audio is None:
            errors.append("Video nao possui faixa de audio")

        probe.close()
    except Exception as e:
        errors.append(f"Erro ao inspecionar video: {e}")

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

async def build_vertical(
    content_id: str,
    media_list: list[str],
    audio_path: str,
    app: dict,
    workspace: dict,
) -> str:
    """
    Monta video vertical (1080x1920) para Instagram Reels / YouTube Shorts.

    Args:
        content_id: ID do conteudo (usado para organizar pasta temporaria)
        media_list: lista de caminhos locais de imagens/videos
        audio_path: caminho do arquivo MP3 de narracao
        app: dict com dados do aplicativo (cta, roteiro via conteudo, etc.)
        workspace: dict com dados do workspace (logo_url, cor_primaria, etc.)

    Returns:
        Caminho absoluto do arquivo MP4 final gerado.

    Raises:
        RuntimeError se a validacao do video falhar.
    """
    app_id = app.get("id")
    video_id = content_id  # usa content_id como referencia

    _log_etapa(app_id, video_id, "video_vertical_inicio", "info",
               "Iniciando montagem do video vertical")

    # Diretorio de trabalho
    pipeline_dir = ensure_pipeline_dir(content_id)
    output_path = os.path.join(pipeline_dir, "vertical.mp4")

    # 1. Carregar audio e obter duracao
    _log_etapa(app_id, video_id, "video_vertical_audio", "info",
               "Carregando audio de narracao")

    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    logger.info(f"Audio carregado: {audio_duration:.1f}s")

    # 2. Distribuir midias proporcionalmente a duracao do audio
    if not media_list:
        raise ValueError("Lista de midias vazia — impossivel montar video")

    clip_duration = audio_duration / len(media_list)
    logger.info(f"Distribuindo {len(media_list)} midias, ~{clip_duration:.1f}s cada")

    _log_etapa(app_id, video_id, "video_vertical_clipes", "info",
               f"Preparando {len(media_list)} clipes ({clip_duration:.1f}s cada)")

    # 3. Criar clipes de midia com fade
    clips = []
    for i, media_path in enumerate(media_list):
        try:
            clip = _make_clip(media_path, clip_duration)

            # Fade in entre clipes
            if i > 0:
                clip = clip.with_effects([CrossFadeIn(FADE_DURATION)])

            clips.append(clip)
            logger.info(f"Clipe {i+1}/{len(media_list)} preparado: {media_path}")
        except Exception as e:
            logger.error(f"Erro ao processar midia {media_path}: {e}")
            # Cria clipe preto como fallback
            fallback = ColorClip(
                size=(WIDTH, HEIGHT), color=(0, 0, 0)
            ).with_duration(clip_duration)
            clips.append(fallback)

    if not clips:
        raise RuntimeError("Nenhum clipe foi gerado com sucesso")

    # 4. Concatenar clipes
    _log_etapa(app_id, video_id, "video_vertical_concat", "info",
               "Concatenando clipes")

    video = concatenate_videoclips(clips, method="compose")

    # 5. Camadas de overlay
    layers = [video]

    # 5a. Legendas sincronizadas
    roteiro = app.get("roteiro", "")
    if roteiro:
        _log_etapa(app_id, video_id, "video_vertical_legendas", "info",
                   "Gerando legendas sincronizadas")
        subtitle_clips = _create_subtitle_clips(roteiro, audio_duration)
        layers.extend(subtitle_clips)

    # 5b. Marca d'agua (logo)
    logo_path = workspace.get("logo_local_path") or workspace.get("logo_url")
    if logo_path and os.path.exists(logo_path):
        _log_etapa(app_id, video_id, "video_vertical_logo", "info",
                   "Adicionando marca d'agua")
        watermark = _create_watermark(logo_path, audio_duration)
        if watermark:
            layers.append(watermark)

    # 5c. CTA nos ultimos 5 segundos
    cta_text = app.get("cta", "")
    if cta_text:
        _log_etapa(app_id, video_id, "video_vertical_cta", "info",
                   "Adicionando CTA final")
        cor_primaria = workspace.get("cor_primaria", "#FFFFFF")
        cta_clip = _create_cta_clip(cta_text, cor_primaria, audio_duration)
        layers.append(cta_clip)

    # 6. Compositar tudo
    _log_etapa(app_id, video_id, "video_vertical_composicao", "info",
               "Compositando camadas do video")

    final = CompositeVideoClip(layers, size=(WIDTH, HEIGHT)).with_duration(audio_duration)
    final = final.with_audio(audio_clip)

    # 7. Exportar MP4
    _log_etapa(app_id, video_id, "video_vertical_export", "info",
               f"Exportando MP4 para {output_path}")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="128k",
        preset="medium",
        threads=4,
        logger="bar",
    )

    # Fechar clipes para liberar recursos
    audio_clip.close()
    for c in clips:
        c.close()
    final.close()

    # 8. Validacao
    _log_etapa(app_id, video_id, "video_vertical_validacao", "info",
               "Validando video gerado")

    result = _validate_output(output_path, audio_duration)

    if not result["valid"]:
        erros = "; ".join(result["errors"])
        _log_etapa(app_id, video_id, "video_vertical_erro", "erro",
                   f"Validacao falhou: {erros}")
        raise RuntimeError(f"Validacao do video falhou: {erros}")

    file_size = os.path.getsize(output_path)
    _log_etapa(app_id, video_id, "video_vertical_sucesso", "sucesso",
               f"Video vertical gerado: {output_path} ({file_size} bytes, {audio_duration:.1f}s)")

    logger.info(f"Video vertical exportado com sucesso: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Helpers parametrizados para formato horizontal
# ---------------------------------------------------------------------------

def _make_clip_sized(
    media_path: str, duration: float, target_w: int, target_h: int,
) -> VideoFileClip | ImageClip:
    """Cria clipe redimensionado/crop para resolucao alvo arbitraria."""
    if _is_video_file(media_path):
        clip = VideoFileClip(media_path)
        clip_ratio = clip.w / clip.h
        target_ratio = target_w / target_h

        if clip_ratio > target_ratio:
            clip = clip.resized(height=target_h)
        else:
            clip = clip.resized(width=target_w)

        clip = clip.cropped(
            x_center=clip.w / 2,
            y_center=clip.h / 2,
            width=target_w,
            height=target_h,
        )

        if clip.duration > duration:
            clip = clip.subclipped(0, duration)
        elif clip.duration < duration:
            clip = clip.looped(duration=duration)

        return clip
    else:
        resized_path = _resize_and_crop_image(media_path, target_w, target_h)
        clip = ImageClip(resized_path).with_duration(duration)
        return clip


def _create_subtitle_clips_sized(
    roteiro: str,
    total_duration: float,
    target_w: int,
    target_h: int,
) -> list[TextClip]:
    """Legendas adaptadas ao formato horizontal: fonte maior, posicao inferior."""
    blocks = _split_script_into_blocks(roteiro, words_per_block=8)
    if not blocks:
        return []

    block_duration = total_duration / len(blocks)
    subtitle_clips = []

    for i, text in enumerate(blocks):
        start = i * block_duration
        wrapped = textwrap.fill(text, width=45)
        txt_clip = (
            TextClip(
                text=wrapped,
                font_size=56,
                color="white",
                font=_FONT_PATH,
                stroke_color="black",
                stroke_width=2,
                text_align="center",
                size=(target_w - 200, None),
            )
            .with_duration(block_duration)
            .with_start(start)
            .with_position(("center", target_h - 160))
        )
        subtitle_clips.append(txt_clip)

    return subtitle_clips


def _create_watermark_sized(
    logo_path: str | None,
    total_duration: float,
    target_w: int,
    target_h: int,
) -> ImageClip | None:
    """Marca d'agua no canto inferior direito, adaptada ao formato."""
    if not logo_path or not os.path.exists(logo_path):
        return None

    logo_img = Image.open(logo_path).convert("RGBA")

    max_logo_w = 150 if target_w >= 1920 else 120
    ratio = max_logo_w / logo_img.width
    new_size = (max_logo_w, int(logo_img.height * ratio))
    logo_img = logo_img.resize(new_size, Image.LANCZOS)

    alpha = logo_img.split()[3]
    alpha = alpha.point(lambda p: int(p * 0.2))
    logo_img.putalpha(alpha)

    tmp_path = logo_path + f"_wm_{target_w}x{target_h}.png"
    logo_img.save(tmp_path, "PNG")

    watermark = (
        ImageClip(tmp_path)
        .with_duration(total_duration)
        .with_position((target_w - new_size[0] - 30, target_h - new_size[1] - 30))
    )
    return watermark


def _create_cta_clip_sized(
    cta_text: str,
    cor_primaria: str,
    total_duration: float,
    target_w: int,
    target_h: int,
) -> TextClip:
    """CTA nos ultimos 5 segundos, adaptado ao formato."""
    cta_start = max(0, total_duration - CTA_DURATION)
    wrapped = textwrap.fill(cta_text, width=35 if target_w >= 1920 else 20)
    cta_clip = (
        TextClip(
            text=wrapped,
            font_size=64 if target_w >= 1920 else 56,
            color=cor_primaria or "#FFFFFF",
            font=_FONT_PATH,
            stroke_color="black",
            stroke_width=2,
            text_align="center",
            size=(target_w - 200, None),
        )
        .with_duration(CTA_DURATION)
        .with_start(cta_start)
        .with_position(("center", target_h // 2 - 60))
        .with_effects([CrossFadeIn(0.5)])
    )
    return cta_clip


def _validate_output_sized(
    output_path: str,
    audio_duration: float,
    target_w: int,
    target_h: int,
    min_dur: int,
    max_dur: int,
) -> dict:
    """Valida video gerado com resolucao e duracao parametrizadas."""
    errors = []

    if not os.path.exists(output_path):
        return {"valid": False, "errors": ["Arquivo de saida nao encontrado"]}

    file_size = os.path.getsize(output_path)
    if file_size < 1_000_000:
        errors.append(f"Arquivo muito pequeno ({file_size} bytes)")

    try:
        probe = VideoFileClip(output_path)
        w, h = probe.size
        dur = probe.duration

        if w != target_w or h != target_h:
            errors.append(f"Resolucao incorreta: {w}x{h} (esperado {target_w}x{target_h})")

        if dur < min_dur:
            errors.append(f"Duracao muito curta: {dur:.1f}s (minimo {min_dur}s)")
        elif dur > max_dur:
            errors.append(f"Duracao muito longa: {dur:.1f}s (maximo {max_dur}s)")

        if probe.audio is None:
            errors.append("Video nao possui faixa de audio")

        probe.close()
    except Exception as e:
        errors.append(f"Erro ao inspecionar video: {e}")

    return {"valid": len(errors) == 0, "errors": errors}


# ---------------------------------------------------------------------------
# build_horizontal — formato 16:9 para YouTube
# ---------------------------------------------------------------------------

async def build_horizontal(
    content_id: str,
    media_list: list[str],
    audio_path: str,
    app: dict,
    workspace: dict,
) -> str:
    """
    Monta video horizontal (1920x1080) para YouTube.

    Args:
        content_id: ID do conteudo
        media_list: lista de caminhos locais de imagens/videos
        audio_path: caminho do arquivo MP3 de narracao
        app: dict com dados do aplicativo
        workspace: dict com dados do workspace

    Returns:
        Caminho absoluto do arquivo MP4 final gerado.
    """
    app_id = app.get("id")
    video_id = content_id

    _log_etapa(app_id, video_id, "video_horizontal_inicio", "info",
               "Iniciando montagem do video horizontal")

    pipeline_dir = ensure_pipeline_dir(content_id)
    output_path = os.path.join(pipeline_dir, "horizontal.mp4")

    # 1. Carregar audio
    _log_etapa(app_id, video_id, "video_horizontal_audio", "info",
               "Carregando audio de narracao")

    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    logger.info(f"Audio carregado: {audio_duration:.1f}s")

    # 2. Distribuir midias
    if not media_list:
        raise ValueError("Lista de midias vazia — impossivel montar video")

    clip_duration = audio_duration / len(media_list)
    logger.info(f"Distribuindo {len(media_list)} midias, ~{clip_duration:.1f}s cada")

    _log_etapa(app_id, video_id, "video_horizontal_clipes", "info",
               f"Preparando {len(media_list)} clipes ({clip_duration:.1f}s cada)")

    # 3. Criar clipes de midia com fade
    clips = []
    for i, media_path in enumerate(media_list):
        try:
            clip = _make_clip_sized(media_path, clip_duration, H_WIDTH, H_HEIGHT)

            if i > 0:
                clip = clip.with_effects([CrossFadeIn(FADE_DURATION)])

            clips.append(clip)
            logger.info(f"Clipe {i+1}/{len(media_list)} preparado: {media_path}")
        except Exception as e:
            logger.error(f"Erro ao processar midia {media_path}: {e}")
            fallback = ColorClip(
                size=(H_WIDTH, H_HEIGHT), color=(0, 0, 0)
            ).with_duration(clip_duration)
            clips.append(fallback)

    if not clips:
        raise RuntimeError("Nenhum clipe foi gerado com sucesso")

    # 4. Concatenar
    _log_etapa(app_id, video_id, "video_horizontal_concat", "info",
               "Concatenando clipes")

    video = concatenate_videoclips(clips, method="compose")

    # 5. Camadas de overlay
    layers = [video]

    # 5a. Legendas sincronizadas (fonte maior, posicao inferior, texto mais largo)
    roteiro = app.get("roteiro", "")
    if roteiro:
        _log_etapa(app_id, video_id, "video_horizontal_legendas", "info",
                   "Gerando legendas sincronizadas")
        subtitle_clips = _create_subtitle_clips_sized(
            roteiro, audio_duration, H_WIDTH, H_HEIGHT,
        )
        layers.extend(subtitle_clips)

    # 5b. Marca d'agua (logo)
    logo_path = workspace.get("logo_local_path") or workspace.get("logo_url")
    if logo_path and os.path.exists(logo_path):
        _log_etapa(app_id, video_id, "video_horizontal_logo", "info",
                   "Adicionando marca d'agua")
        watermark = _create_watermark_sized(
            logo_path, audio_duration, H_WIDTH, H_HEIGHT,
        )
        if watermark:
            layers.append(watermark)

    # 5c. CTA nos ultimos 5 segundos
    cta_text = app.get("cta", "")
    if cta_text:
        _log_etapa(app_id, video_id, "video_horizontal_cta", "info",
                   "Adicionando CTA final")
        cor_primaria = workspace.get("cor_primaria", "#FFFFFF")
        cta_clip = _create_cta_clip_sized(
            cta_text, cor_primaria, audio_duration, H_WIDTH, H_HEIGHT,
        )
        layers.append(cta_clip)

    # 6. Compositar
    _log_etapa(app_id, video_id, "video_horizontal_composicao", "info",
               "Compositando camadas do video")

    final = CompositeVideoClip(layers, size=(H_WIDTH, H_HEIGHT)).with_duration(audio_duration)
    final = final.with_audio(audio_clip)

    # 7. Exportar MP4
    _log_etapa(app_id, video_id, "video_horizontal_export", "info",
               f"Exportando MP4 para {output_path}")

    final.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="128k",
        preset="medium",
        threads=4,
        logger="bar",
    )

    # Fechar clipes
    audio_clip.close()
    for c in clips:
        c.close()
    final.close()

    # 8. Validacao
    _log_etapa(app_id, video_id, "video_horizontal_validacao", "info",
               "Validando video gerado")

    result = _validate_output_sized(
        output_path, audio_duration, H_WIDTH, H_HEIGHT, H_MIN_DURATION, H_MAX_DURATION,
    )

    if not result["valid"]:
        erros = "; ".join(result["errors"])
        _log_etapa(app_id, video_id, "video_horizontal_erro", "erro",
                   f"Validacao falhou: {erros}")
        raise RuntimeError(f"Validacao do video horizontal falhou: {erros}")

    file_size = os.path.getsize(output_path)
    _log_etapa(app_id, video_id, "video_horizontal_sucesso", "sucesso",
               f"Video horizontal gerado: {output_path} ({file_size} bytes, {audio_duration:.1f}s)")

    logger.info(f"Video horizontal exportado com sucesso: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# Orquestrador — build_all_formats
# ---------------------------------------------------------------------------

async def _upload_video_to_storage(
    file_path: str,
    content_id: str,
    formato: str,
) -> str:
    """Faz upload do video para Supabase Storage (bucket 'videos') e retorna URL."""
    from core.db import get_supabase
    from core.config import get_settings

    bucket = "videos"
    ext = os.path.splitext(file_path)[1]
    storage_path = f"{content_id}/{formato}{ext}"

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    supabase = get_supabase()
    supabase.storage.from_(bucket).upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": "video/mp4"},
    )

    settings = get_settings()
    public_url = f"{settings.supabase_url}/storage/v1/object/public/{bucket}/{storage_path}"
    logger.info(f"Video {formato} enviado para Storage: {public_url}")
    return public_url


def _get_video_duration(file_path: str) -> float:
    """Retorna duracao do video em segundos."""
    clip = VideoFileClip(file_path)
    dur = clip.duration
    clip.close()
    return dur


async def build_all_formats(
    content_id: str,
    app: dict,
    workspace: dict,
) -> VideoOutput:
    """
    Orquestra a montagem de videos em todos os formatos configurados para o app.

    Fluxo:
    1. Busca conteudo e seleciona midias
    2. Gera audio TTS
    3. Monta vertical e/ou horizontal conforme app.formato_youtube
    4. Faz upload para Supabase Storage (bucket 'videos')
    5. Cria/atualiza registro na tabela 'videos'
    6. Status -> 'aguardando_aprovacao'

    Args:
        content_id: ID do conteudo gerado (tabela conteudos)
        app: dict com dados do aplicativo
        workspace: dict com dados do workspace

    Returns:
        VideoOutput com caminhos e URLs dos videos gerados
    """
    from core.db import get_supabase
    from modules.video_engine.services.tts import generate_audio, get_default_voice
    from modules.video_engine.services.media_selector import select_media_for_script

    app_id = app.get("id")
    output = VideoOutput()

    _log_etapa(app_id, None, "build_all_inicio", "info",
               f"Iniciando build_all_formats para conteudo {content_id}")

    # 1. Buscar conteudo do banco
    supabase = get_supabase()
    conteudo_result = (
        supabase.table("conteudos")
        .select("*")
        .eq("id", content_id)
        .execute()
    )

    if not conteudo_result.data:
        raise ValueError(f"Conteudo {content_id} nao encontrado")

    conteudo = conteudo_result.data[0]
    roteiro = conteudo.get("roteiro", "")

    if not roteiro:
        raise ValueError("Roteiro vazio no conteudo")

    # Atualizar status do conteudo para processando_video
    supabase.table("conteudos").update(
        {"status": "processando_video"}
    ).eq("id", content_id).execute()

    # 2. Gerar audio TTS
    _log_etapa(app_id, None, "build_all_tts", "info", "Gerando audio TTS")

    idioma = workspace.get("idioma", "pt-BR")
    voice = get_default_voice(idioma)
    pipeline_dir = ensure_pipeline_dir(content_id)
    audio_path = os.path.join(pipeline_dir, "narration.mp3")

    audio_meta = await generate_audio(
        roteiro=roteiro,
        voice=voice,
        output_path=audio_path,
    )

    # 3. Selecionar midias
    _log_etapa(app_id, None, "build_all_media", "info", "Selecionando midias")

    keywords_visuais = conteudo.get("keywords_visuais", [])
    workspace_id = app.get("workspace_id", workspace.get("id"))
    media_list = await select_media_for_script(
        app_id=app_id,
        workspace_id=workspace_id,
        visual_keywords=keywords_visuais,
        min_count=5,
        video_id=content_id,
    )

    if not media_list:
        raise ValueError("Nenhuma midia selecionada para o video")

    # Enriquecer app com roteiro para as funcoes de build
    app_with_roteiro = {**app, "roteiro": roteiro}

    # 4. Determinar quais formatos gerar
    plataformas = app.get("plataformas", [])
    formato_youtube = app.get("formato_youtube", "ambos")

    gerar_vertical = "instagram" in plataformas or formato_youtube in ("9_16", "ambos")
    gerar_horizontal = "youtube" in plataformas and formato_youtube in ("16_9", "ambos")

    # 5. Montar videos
    if gerar_vertical:
        _log_etapa(app_id, None, "build_all_vertical", "info",
                   "Montando video vertical")
        output.vertical_path = await build_vertical(
            content_id=content_id,
            media_list=media_list,
            audio_path=audio_path,
            app=app_with_roteiro,
            workspace=workspace,
        )
        output.vertical_duration = _get_video_duration(output.vertical_path)

    if gerar_horizontal:
        _log_etapa(app_id, None, "build_all_horizontal", "info",
                   "Montando video horizontal")
        output.horizontal_path = await build_horizontal(
            content_id=content_id,
            media_list=media_list,
            audio_path=audio_path,
            app=app_with_roteiro,
            workspace=workspace,
        )
        output.horizontal_duration = _get_video_duration(output.horizontal_path)

    # 6. Upload para Supabase Storage (bucket 'videos')
    _log_etapa(app_id, None, "build_all_upload", "info",
               "Enviando videos para Supabase Storage")

    if output.vertical_path:
        output.vertical_url = await _upload_video_to_storage(
            output.vertical_path, content_id, "vertical",
        )

    if output.horizontal_path:
        output.horizontal_url = await _upload_video_to_storage(
            output.horizontal_path, content_id, "horizontal",
        )

    # 7. Criar registro na tabela 'videos'
    _log_etapa(app_id, None, "build_all_registro", "info",
               "Criando registro na tabela videos")

    total_bytes = 0
    if output.vertical_path:
        total_bytes += os.path.getsize(output.vertical_path)
    if output.horizontal_path:
        total_bytes += os.path.getsize(output.horizontal_path)

    video_data = {
        "conteudo_id": content_id,
        "negocio_id": app_id,
        "url_storage_vertical": output.vertical_url,
        "duracao_vertical_segundos": int(output.vertical_duration) if output.vertical_duration else None,
        "url_storage_horizontal": output.horizontal_url,
        "duracao_horizontal_segundos": int(output.horizontal_duration) if output.horizontal_duration else None,
        "tamanho_bytes_total": total_bytes,
        "status": "aguardando_aprovacao",
        "criado_em": datetime.now(timezone.utc).isoformat(),
    }

    video_result = supabase.table("videos").insert(video_data).execute()
    output.video_id = video_result.data[0]["id"]

    # 8. Atualizar status do conteudo
    supabase.table("conteudos").update(
        {"status": "aguardando_aprovacao"}
    ).eq("id", content_id).execute()

    _log_etapa(app_id, output.video_id, "build_all_sucesso", "sucesso",
               f"Videos gerados e enviados. video_id={output.video_id}")

    logger.info(f"build_all_formats concluido: video_id={output.video_id}")
    return output
