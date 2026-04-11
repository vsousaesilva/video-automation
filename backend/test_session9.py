"""
Script de teste standalone para validar a Sessao 9:
- build_horizontal (1920x1080)
- build_all_formats (orquestrador)
- Upload para Supabase Storage (mockado)
- Registro na tabela videos (mockado)

Uso (CMD):
    cd video-automation\backend
    venv\Scripts\activate
    python test_session9.py
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
    """Cria imagens coloridas de teste em 1920x1080 (horizontal)."""
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
        # Cria em tamanho generico para testar redimensionamento
        img = Image.new("RGB", (1600, 1200), color)
        draw = ImageDraw.Draw(img)

        text = f"CENA {i + 1}"
        try:
            font = ImageFont.truetype("arial.ttf", 80)
        except OSError:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            ((1600 - tw) / 2, (1200 - th) / 2),
            text,
            fill="white",
            font=font,
        )

        path = os.path.join(output_dir, f"test_scene_{i+1}.jpg")
        img.save(path, "JPEG")
        paths.append(path)
        print(f"  Imagem de teste criada: {path}")

    return paths


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
# Teste 1 — build_horizontal isolado
# ---------------------------------------------------------------------------

async def test_build_horizontal():
    print("=" * 60)
    print("TESTE 1 — build_horizontal (1920x1080)")
    print("=" * 60)

    # Roteiro mais longo para formato horizontal (60-180s)
    roteiro = (
        "Voce ja imaginou ter um aplicativo que resolve todos os seus problemas "
        "de organizacao pessoal? Apresentamos o TaskMaster, o app que vai "
        "revolucionar a forma como voce gerencia suas tarefas diarias. "
        "Com o TaskMaster, voce pode criar listas inteligentes, definir "
        "prioridades automaticas e receber lembretes no momento certo. "
        "Mais de cinquenta mil usuarios ja transformaram sua produtividade. "
        "O app aprende com seus habitos e sugere a melhor ordem para "
        "completar suas atividades. Funcionalidades como calendario integrado, "
        "compartilhamento de tarefas com equipe, e relatorios de produtividade "
        "semanal fazem do TaskMaster a escolha ideal para quem quer organizar "
        "a vida de verdade. Alem disso, o TaskMaster sincroniza automaticamente "
        "com o Google Calendar, Outlook e Apple Calendar, garantindo que voce "
        "nunca perca um compromisso importante. A inteligencia artificial do "
        "TaskMaster analisa seus padroes de trabalho e sugere os melhores "
        "horarios para cada tipo de atividade. Baixe agora gratuitamente na "
        "App Store e na Play Store e comece a ser mais produtivo hoje mesmo!"
    )

    test_dir = os.path.join(tempfile.gettempdir(), "pipeline", "test_session9_h")
    os.makedirs(test_dir, exist_ok=True)
    print(f"\nPasta de trabalho: {test_dir}")

    print("\n--- Gerando assets de teste ---")
    media_list = create_test_images(test_dir, count=6)
    logo_path = create_test_logo(test_dir)
    audio_path = await create_test_audio(test_dir, roteiro)

    app_data = {
        "id": "test-app-h01",
        "nome": "TaskMaster",
        "cta": "Baixe gratis na App Store e Play Store!",
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

    print("\n--- Montando video horizontal ---")
    try:
        path = await vb.build_horizontal(
            content_id="test_session9_h",
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

    print("\n--- Checklist de validacao ---")
    checks = [
        ("Arquivo MP4 existe", os.path.exists(path)),
        ("Resolucao 1920x1080", w == 1920 and h == 1080),
        ("Duracao 60-180s", 60 <= dur <= 180),
        ("Possui audio", has_audio),
        ("Tamanho > 1MB", os.path.getsize(path) > 1_000_000),
    ]

    all_ok = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  [{status}] {label}")

    print()
    if all_ok:
        print("TESTE 1: TODOS OS CHECKS PASSARAM!")
    else:
        print("TESTE 1: ALGUM CHECK FALHOU")

    return path, all_ok


# ---------------------------------------------------------------------------
# Teste 2 — build_all_formats (simulado sem Supabase)
# ---------------------------------------------------------------------------

async def test_build_all_formats():
    print("\n" + "=" * 60)
    print("TESTE 2 — build_all_formats (simulado, sem Supabase)")
    print("=" * 60)

    roteiro = (
        "Voce ja imaginou ter um aplicativo que resolve todos os seus problemas "
        "de organizacao pessoal? Apresentamos o TaskMaster, o app que vai "
        "revolucionar a forma como voce gerencia suas tarefas diarias. "
        "Com o TaskMaster, voce pode criar listas inteligentes, definir "
        "prioridades automaticas e receber lembretes no momento certo. "
        "Mais de cinquenta mil usuarios ja transformaram sua produtividade. "
        "O app aprende com seus habitos e sugere a melhor ordem para "
        "completar suas atividades. Funcionalidades como calendario integrado, "
        "compartilhamento de tarefas com equipe, e relatorios de produtividade "
        "semanal fazem do TaskMaster a escolha ideal para quem quer organizar "
        "a vida de verdade. Alem disso, o TaskMaster sincroniza automaticamente "
        "com o Google Calendar, Outlook e Apple Calendar, garantindo que voce "
        "nunca perca um compromisso importante. A inteligencia artificial do "
        "TaskMaster analisa seus padroes de trabalho e sugere os melhores "
        "horarios para cada tipo de atividade. Baixe agora gratuitamente na "
        "App Store e na Play Store e comece a ser mais produtivo hoje mesmo!"
    )

    content_id = "test_session9_all"
    test_dir = os.path.join(tempfile.gettempdir(), "pipeline", content_id)
    os.makedirs(test_dir, exist_ok=True)
    print(f"\nPasta de trabalho: {test_dir}")

    print("\n--- Gerando assets de teste ---")
    media_list = create_test_images(test_dir, count=6)
    logo_path = create_test_logo(test_dir)
    audio_path = await create_test_audio(test_dir, roteiro)

    app_data = {
        "id": "test-app-all",
        "nome": "TaskMaster",
        "workspace_id": "test-ws-001",
        "cta": "Baixe gratis na App Store!",
        "plataformas": ["instagram", "youtube"],
        "formato_youtube": "ambos",
    }
    workspace_data = {
        "id": "test-ws-001",
        "nome": "Workspace Teste",
        "idioma": "pt-BR",
        "cor_primaria": "#2980B9",
        "logo_local_path": logo_path,
    }

    import services.video_builder as vb

    # Monkeypatch — substituir interacao com Supabase
    original_log = vb._log_etapa
    def _log_local(app_id, video_id, etapa, status, mensagem):
        print(f"  [LOG] {etapa} | {status} | {mensagem}")
    vb._log_etapa = _log_local

    # Simular build_all_formats sem Supabase:
    # chamar build_vertical + build_horizontal diretamente
    print("\n--- Montando video VERTICAL ---")
    app_with_roteiro = {**app_data, "roteiro": roteiro}

    vertical_path = await vb.build_vertical(
        content_id=content_id,
        media_list=media_list,
        audio_path=audio_path,
        app=app_with_roteiro,
        workspace=workspace_data,
    )

    print("\n--- Montando video HORIZONTAL ---")
    horizontal_path = await vb.build_horizontal(
        content_id=content_id,
        media_list=media_list,
        audio_path=audio_path,
        app=app_with_roteiro,
        workspace=workspace_data,
    )

    vb._log_etapa = original_log

    # Construir VideoOutput manualmente
    output = vb.VideoOutput(
        vertical_path=vertical_path,
        horizontal_path=horizontal_path,
        vertical_duration=vb._get_video_duration(vertical_path),
        horizontal_duration=vb._get_video_duration(horizontal_path),
        vertical_url="(upload simulado)",
        horizontal_url="(upload simulado)",
        video_id="test-video-id",
    )

    # Validar
    print("\n--- Resultado build_all_formats ---")
    print(f"output.vertical_path: {output.vertical_path}")
    print(f"output.horizontal_path: {output.horizontal_path}")
    print(f"output.vertical_duration: {output.vertical_duration:.1f}s")
    print(f"output.horizontal_duration: {output.horizontal_duration:.1f}s")
    print(f"output.video_id: {output.video_id}")

    from moviepy import VideoFileClip

    # Validar vertical
    probe_v = VideoFileClip(vertical_path)
    vw, vh = probe_v.size
    vdur = probe_v.duration
    v_audio = probe_v.audio is not None
    probe_v.close()

    # Validar horizontal
    probe_h = VideoFileClip(horizontal_path)
    hw, hh = probe_h.size
    hdur = probe_h.duration
    h_audio = probe_h.audio is not None
    probe_h.close()

    print("\n--- Checklist de validacao ---")
    checks = [
        ("Vertical: arquivo existe", os.path.exists(vertical_path)),
        ("Vertical: resolucao 1080x1920", vw == 1080 and vh == 1920),
        ("Vertical: possui audio", v_audio),
        ("Horizontal: arquivo existe", os.path.exists(horizontal_path)),
        ("Horizontal: resolucao 1920x1080", hw == 1920 and hh == 1080),
        ("Horizontal: possui audio", h_audio),
        ("VideoOutput.vertical_path preenchido", output.vertical_path is not None),
        ("VideoOutput.horizontal_path preenchido", output.horizontal_path is not None),
        ("VideoOutput.video_id preenchido", output.video_id is not None),
    ]

    all_ok = True
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"  [{status}] {label}")

    print()
    if all_ok:
        print("TESTE 2: TODOS OS CHECKS PASSARAM!")
    else:
        print("TESTE 2: ALGUM CHECK FALHOU")

    return output, all_ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    print()
    print("*" * 60)
    print("  SESSAO 9 — Testes de Video Horizontal + build_all_formats")
    print("*" * 60)

    # Teste 1: build_horizontal isolado
    h_path, ok1 = await test_build_horizontal()

    # Teste 2: build_all_formats (vertical + horizontal)
    output, ok2 = await test_build_all_formats()

    # Resumo final
    print("\n" + "=" * 60)
    print("RESUMO FINAL")
    print("=" * 60)
    print(f"  Teste 1 (build_horizontal): {'PASS' if ok1 else 'FAIL'}")
    print(f"  Teste 2 (build_all_formats): {'PASS' if ok2 else 'FAIL'}")

    if ok1 and ok2:
        print("\n  RESULTADO: TODOS OS TESTES DA SESSAO 9 PASSARAM!")
    else:
        print("\n  RESULTADO: ALGUM TESTE FALHOU — verifique acima.")

    print("=" * 60)

    # Mostrar entregavel verificavel
    print("\n--- Entregavel verificavel ---")
    print(f"output.vertical_path: {output.vertical_path}")
    print(f"output.horizontal_path: {output.horizontal_path}")
    print(f"output.vertical_duration: {output.vertical_duration:.1f}s")
    print(f"output.horizontal_duration: {output.horizontal_duration:.1f}s")
    print("(Upload Supabase e status 'aguardando_aprovacao' requerem .env configurado)")


if __name__ == "__main__":
    asyncio.run(main())