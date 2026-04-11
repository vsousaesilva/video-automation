"""
Script de teste standalone para validar o build_vertical da Sessao 8.
Gera midias de teste (imagens coloridas) e audio TTS real via Edge TTS,
monta o video vertical e valida o resultado.

Uso (CMD):
    cd video-automation\backend
    venv\Scripts\activate
    python test_video_builder.py
"""

import asyncio
import os
import sys
import tempfile

# Adiciona o diretorio backend ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont


# ---------------------------------------------------------------------------
# 1. Gerar imagens de teste
# ---------------------------------------------------------------------------

def create_test_images(output_dir: str, count: int = 5) -> list[str]:
    """Cria imagens coloridas de teste em 1080x1920."""
    colors = [
        (41, 128, 185),   # azul
        (39, 174, 96),    # verde
        (192, 57, 43),    # vermelho
        (142, 68, 173),   # roxo
        (243, 156, 18),   # laranja
        (44, 62, 80),     # cinza escuro
        (22, 160, 133),   # teal
    ]
    paths = []
    for i in range(count):
        color = colors[i % len(colors)]
        img = Image.new("RGB", (1080, 1920), color)
        draw = ImageDraw.Draw(img)

        # Texto indicativo
        text = f"CENA {i + 1}"
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((1080 - tw) / 2, (1920 - th) / 2),
            text,
            fill="white",
            font=font,
        )

        path = os.path.join(output_dir, f"test_scene_{i+1}.jpg")
        img.save(path, "JPEG")
        paths.append(path)
        print(f"  Imagem de teste criada: {path}")

    return paths


# ---------------------------------------------------------------------------
# 2. Gerar logo de teste
# ---------------------------------------------------------------------------

def create_test_logo(output_dir: str) -> str:
    """Cria um logo PNG simples para marca d'agua."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([10, 10, 190, 190], fill=(255, 255, 255, 255))
    draw.ellipse([30, 30, 170, 170], fill=(41, 128, 185, 255))

    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except OSError:
        font = ImageFont.load_default()

    draw.text((65, 75), "VA", fill="white", font=font)

    path = os.path.join(output_dir, "test_logo.png")
    img.save(path, "PNG")
    print(f"  Logo de teste criado: {path}")
    return path


# ---------------------------------------------------------------------------
# 3. Gerar audio TTS de teste
# ---------------------------------------------------------------------------

async def create_test_audio(output_dir: str, roteiro: str) -> str:
    """Gera audio MP3 de teste via Edge TTS."""
    from services.tts import generate_audio

    metadata = await generate_audio(
        roteiro=roteiro,
        voice="pt-BR-FranciscaNeural",
        output_path=os.path.join(output_dir, "narration.mp3"),
    )
    print(f"  Audio gerado: {metadata.file_path} ({metadata.duration_seconds:.1f}s)")
    return metadata.file_path


# ---------------------------------------------------------------------------
# 4. Executar build_vertical e validar
# ---------------------------------------------------------------------------

async def main():
    print("=" * 60)
    print("TESTE — Sessao 8: Montagem de Video Vertical")
    print("=" * 60)

    # Roteiro de teste (~45 segundos de fala)
    roteiro = (
        "Voce ja imaginou ter um aplicativo que resolve todos os seus problemas "
        "de organizacao pessoal? Apresentamos o TaskMaster, o app que vai "
        "revolucionar a forma como voce gerencia suas tarefas diarias. "
        "Com o TaskMaster, voce pode criar listas inteligentes, definir "
        "prioridades automaticas e receber lembretes no momento certo. "
        "Mais de cinquenta mil usuarios ja transformaram sua produtividade. "
        "O app aprende com seus habitos e sugere a melhor ordem para "
        "completar suas atividades. Baixe agora gratuitamente na App Store "
        "e na Play Store e comece a ser mais produtivo hoje mesmo!"
    )

    # Pasta temporaria
    test_dir = os.path.join(tempfile.gettempdir(), "pipeline", "test_session8")
    os.makedirs(test_dir, exist_ok=True)
    print(f"\nPasta de trabalho: {test_dir}")

    # Gerar assets de teste
    print("\n--- Gerando assets de teste ---")
    media_list = create_test_images(test_dir, count=5)
    logo_path = create_test_logo(test_dir)
    audio_path = await create_test_audio(test_dir, roteiro)

    # Dados simulados (sem Supabase)
    app_data = {
        "id": "test-app-001",
        "nome": "TaskMaster",
        "cta": "Baixe gratis na App Store!",
        "roteiro": roteiro,
    }
    workspace_data = {
        "id": "test-ws-001",
        "nome": "Workspace Teste",
        "cor_primaria": "#2980B9",
        "logo_local_path": logo_path,
    }

    # Monkeypatch para evitar chamadas ao Supabase nos logs
    import services.video_builder as vb
    original_log = vb._log_etapa
    def _log_local(app_id, video_id, etapa, status, mensagem):
        print(f"  [LOG] {etapa} | {status} | {mensagem}")
    vb._log_etapa = _log_local

    # Executar build
    print("\n--- Montando video vertical ---")
    try:
        path = await vb.build_vertical(
            content_id="test_session8",
            media_list=media_list,
            audio_path=audio_path,
            app=app_data,
            workspace=workspace_data,
        )
    finally:
        vb._log_etapa = original_log

    # Validar resultado
    print("\n--- Resultado ---")
    print(f"Arquivo: {path}")
    print(f"Tamanho: {os.path.getsize(path):,} bytes")

    from moviepy import VideoFileClip
    probe = VideoFileClip(path)
    w, h = probe.size
    dur = probe.duration
    has_audio = probe.audio is not None
    probe.close()

    print(f"Resolucao: {w}x{h}")
    print(f"Duracao: {dur:.1f}s")
    print(f"Audio: {'Sim' if has_audio else 'Nao'}")

    # Checklist
    print("\n--- Checklist de validacao ---")
    checks = [
        ("Arquivo MP4 existe", os.path.exists(path)),
        ("Resolucao 1080x1920", w == 1080 and h == 1920),
        ("Duracao 30-90s", 30 <= dur <= 90),
        ("Possui audio", has_audio),
        ("Tamanho > 1MB", os.path.getsize(path) > 1_000_000),
    ]

    all_ok = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  [{status}] {label}")

    print("\n" + "=" * 60)
    if all_ok:
        print("RESULTADO: TODOS OS TESTES PASSARAM!")
    else:
        print("RESULTADO: ALGUM TESTE FALHOU — verifique acima.")
    print("=" * 60)

    return path


if __name__ == "__main__":
    result = asyncio.run(main())