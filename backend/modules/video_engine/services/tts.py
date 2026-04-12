import asyncio
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import edge_tts
from mutagen.mp3 import MP3

logger = logging.getLogger(__name__)

VOZES_PADRAO = {
    "pt-BR": {
        "feminina": "pt-BR-FranciscaNeural",
        "masculino": "pt-BR-AntonioNeural",
    },
    "en-US": {
        "feminina": "en-US-JennyNeural",
        "masculino": "en-US-GuyNeural",
    },
    "es-ES": {
        "feminina": "es-ES-ElviraNeural",
        "masculino": "es-ES-AlvaroNeural",
    },
}

PIPELINE_TMP_DIR = os.path.join(tempfile.gettempdir(), "pipeline")


@dataclass
class AudioMetadata:
    file_path: str
    duration_seconds: float
    voice: str
    size_bytes: int


def get_default_voice(idioma: str = "pt-BR", genero: str = "feminina") -> str:
    """Retorna a voz padrao para o idioma e genero informados."""
    voices = VOZES_PADRAO.get(idioma, VOZES_PADRAO["pt-BR"])
    return voices.get(genero, voices["feminina"])


def ensure_pipeline_dir(video_id: str | None = None) -> str:
    """Cria e retorna o diretorio temporario do pipeline."""
    if video_id:
        path = os.path.join(PIPELINE_TMP_DIR, video_id)
    else:
        path = os.path.join(PIPELINE_TMP_DIR, uuid.uuid4().hex)
    os.makedirs(path, exist_ok=True)
    return path


def cleanup_pipeline_dir(pipeline_path: str) -> None:
    """Remove o diretorio temporario do pipeline e seu conteudo."""
    import shutil
    if os.path.exists(pipeline_path) and pipeline_path.startswith(PIPELINE_TMP_DIR):
        shutil.rmtree(pipeline_path, ignore_errors=True)
        logger.info(f"Pasta temporaria removida: {pipeline_path}")


async def generate_audio(
    roteiro: str,
    voice: str = "pt-BR-FranciscaNeural",
    output_path: str | None = None,
) -> AudioMetadata:
    """
    Converte texto em audio MP3 usando Edge TTS.

    Args:
        roteiro: texto a ser convertido em audio
        voice: identificador da voz Edge TTS
        output_path: caminho do arquivo MP3 de saida.
                     Se None, gera em pasta temporaria.

    Returns:
        AudioMetadata com caminho, duracao, voz e tamanho
    """
    if not roteiro or not roteiro.strip():
        raise ValueError("Roteiro vazio")

    if output_path is None:
        tmp_dir = ensure_pipeline_dir()
        output_path = os.path.join(tmp_dir, "narration.mp3")

    # Garante que o diretorio de saida existe
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    logger.info(f"Gerando audio TTS com voz '{voice}' -> {output_path}")

    communicate = edge_tts.Communicate(roteiro, voice)
    await communicate.save(output_path)

    # Verifica se o arquivo foi gerado
    if not os.path.exists(output_path):
        raise RuntimeError(f"Falha ao gerar audio: arquivo nao criado em {output_path}")

    size_bytes = os.path.getsize(output_path)
    if size_bytes == 0:
        raise RuntimeError("Arquivo de audio gerado esta vazio")

    # Obtem duracao via mutagen
    audio_info = MP3(output_path)
    duration_seconds = round(audio_info.info.length, 2)

    logger.info(f"Audio gerado: {duration_seconds}s, {size_bytes} bytes")

    return AudioMetadata(
        file_path=output_path,
        duration_seconds=duration_seconds,
        voice=voice,
        size_bytes=size_bytes,
    )
