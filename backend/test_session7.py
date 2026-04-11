"""
Teste verificavel da Sessao 7: TTS + Selecao de Midia.

Executa:
  1. Gera audio MP3 a partir de texto via Edge TTS
  2. Verifica duracao e existencia do arquivo
  3. Testa pipeline dir e cleanup

Uso:
  cd video-automation/backend
  ..\venv\Scripts\python test_session7.py
"""

import asyncio
import os
import sys
import tempfile

# Garante imports do backend
sys.path.insert(0, os.path.dirname(__file__))

from services.tts import (
    generate_audio,
    ensure_pipeline_dir,
    cleanup_pipeline_dir,
    get_default_voice,
    VOZES_PADRAO,
)


async def test_tts():
    print("=" * 60)
    print("TESTE 1: Geracao de audio via Edge TTS")
    print("=" * 60)

    output_path = os.path.join(tempfile.gettempdir(), "test_session7.mp3")

    # Remove arquivo anterior se existir
    if os.path.exists(output_path):
        os.remove(output_path)

    audio = await generate_audio(
        "Ola, este e um teste de narracao. A plataforma de automacao de videos esta funcionando corretamente.",
        "pt-BR-FranciscaNeural",
        output_path,
    )

    print(f"  Arquivo: {audio.file_path}")
    print(f"  Duracao: {audio.duration_seconds}s")
    print(f"  Tamanho: {audio.size_bytes} bytes")
    print(f"  Voz: {audio.voice}")
    print(f"  Arquivo existe: {os.path.exists(audio.file_path)}")

    assert os.path.exists(audio.file_path), "Arquivo MP3 nao foi criado"
    assert audio.duration_seconds > 1, "Duracao muito curta"
    assert audio.size_bytes > 1000, "Arquivo muito pequeno"

    print("  [OK] Audio gerado com sucesso!\n")
    return audio


async def test_vozes():
    print("=" * 60)
    print("TESTE 2: Vozes disponiveis e funcao get_default_voice")
    print("=" * 60)

    for idioma, vozes in VOZES_PADRAO.items():
        for genero, voz in vozes.items():
            print(f"  {idioma} / {genero}: {voz}")

    voz_fem = get_default_voice("pt-BR", "feminina")
    voz_masc = get_default_voice("pt-BR", "masculino")
    print(f"\n  Padrao feminina pt-BR: {voz_fem}")
    print(f"  Padrao masculino pt-BR: {voz_masc}")

    assert voz_fem == "pt-BR-FranciscaNeural"
    assert voz_masc == "pt-BR-AntonioNeural"

    # Teste com idioma inexistente (deve cair no fallback pt-BR)
    voz_fallback = get_default_voice("xx-XX", "feminina")
    assert voz_fallback == "pt-BR-FranciscaNeural"

    print("  [OK] Vozes configuradas corretamente!\n")


async def test_pipeline_dir():
    print("=" * 60)
    print("TESTE 3: Pasta temporaria do pipeline e cleanup")
    print("=" * 60)

    video_id = "test-video-session7"
    pipeline_path = ensure_pipeline_dir(video_id)
    print(f"  Pipeline dir: {pipeline_path}")
    assert os.path.isdir(pipeline_path), "Diretorio nao foi criado"

    # Cria arquivo dummy para testar cleanup
    dummy_file = os.path.join(pipeline_path, "dummy.txt")
    with open(dummy_file, "w") as f:
        f.write("teste")
    assert os.path.exists(dummy_file)

    cleanup_pipeline_dir(pipeline_path)
    assert not os.path.exists(pipeline_path), "Diretorio nao foi removido"

    print("  [OK] Pipeline dir criado e limpo com sucesso!\n")


async def test_audio_voz_masculina():
    print("=" * 60)
    print("TESTE 4: Audio com voz masculina")
    print("=" * 60)

    output_path = os.path.join(tempfile.gettempdir(), "test_session7_masc.mp3")

    if os.path.exists(output_path):
        os.remove(output_path)

    audio = await generate_audio(
        "Este e um teste com a voz masculina do Antonio.",
        "pt-BR-AntonioNeural",
        output_path,
    )

    print(f"  Duracao: {audio.duration_seconds}s")
    print(f"  Voz: {audio.voice}")
    assert audio.voice == "pt-BR-AntonioNeural"
    assert audio.duration_seconds > 1

    print("  [OK] Voz masculina funcionando!\n")


async def main():
    print("\n" + "#" * 60)
    print("  SESSAO 7 — Teste de TTS e Pipeline")
    print("#" * 60 + "\n")

    try:
        await test_tts()
        await test_vozes()
        await test_pipeline_dir()
        await test_audio_voz_masculina()

        print("=" * 60)
        print("  TODOS OS TESTES PASSARAM!")
        print("=" * 60)

    except Exception as e:
        print(f"\n  [ERRO] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())