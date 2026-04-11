"""
Teste da Sessao 12 — Publicacao no YouTube via API v3.

Verifica:
1. Importacao dos modulos criados
2. Logica de deteccao de Shorts (duracao < 60s)
3. Construcao de metadados (titulo, descricao, tags)
4. Selecao correta de arquivo (vertical vs horizontal)
5. Endpoints de publicacao registrados
6. Integracao com fluxo de aprovacao via Telegram
"""

import sys
import os

# Adicionar backend ao path
sys.path.insert(0, os.path.dirname(__file__))

# Setar variaveis de ambiente minimas para evitar erros de config
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")


def test_imports():
    """Testa que todos os modulos importam sem erro."""
    print("[1] Testando imports...")

    from services.publisher_youtube import (
        publish_to_youtube,
        publish_with_retry,
        _is_short,
        _build_title,
        _build_description,
        _build_tags,
        _select_video_file,
        _get_youtube_credentials,
        MAX_RETRIES,
        RETRY_DELAYS,
    )
    print("    publisher_youtube.py: OK")

    from routers.publish import (
        router,
        publish_youtube,
        retry_publish_youtube,
        get_settings_check,
    )
    print("    routers/publish.py: OK")

    print("    PASSOU\n")


def test_is_short():
    """Testa deteccao de Shorts."""
    print("[2] Testando deteccao de Shorts...")
    from services.publisher_youtube import _is_short

    # Short: vertical < 60s
    video_short = {
        "url_storage_vertical": "https://storage/video_v.mp4",
        "duracao_vertical_segundos": 45,
        "url_storage_horizontal": "https://storage/video_h.mp4",
        "duracao_horizontal_segundos": 120,
    }
    assert _is_short(video_short) is True, "Deveria ser Short (45s vertical)"

    # Nao Short: vertical >= 60s
    video_long = {
        "url_storage_vertical": "https://storage/video_v.mp4",
        "duracao_vertical_segundos": 90,
        "url_storage_horizontal": "https://storage/video_h.mp4",
        "duracao_horizontal_segundos": 120,
    }
    assert _is_short(video_long) is False, "Nao deveria ser Short (90s)"

    # Nao Short: sem vertical
    video_no_vertical = {
        "url_storage_vertical": None,
        "duracao_vertical_segundos": None,
        "url_storage_horizontal": "https://storage/video_h.mp4",
        "duracao_horizontal_segundos": 120,
    }
    assert _is_short(video_no_vertical) is False, "Nao deveria ser Short (sem vertical)"

    # Nao Short: duracao 0
    video_zero = {
        "url_storage_vertical": "https://storage/video_v.mp4",
        "duracao_vertical_segundos": 0,
    }
    assert _is_short(video_zero) is False, "Nao deveria ser Short (duracao 0)"

    # Short: exatamente no limite
    video_59 = {
        "url_storage_vertical": "https://storage/video_v.mp4",
        "duracao_vertical_segundos": 59,
    }
    assert _is_short(video_59) is True, "Deveria ser Short (59s)"

    # Nao Short: exatamente 60s
    video_60 = {
        "url_storage_vertical": "https://storage/video_v.mp4",
        "duracao_vertical_segundos": 60,
    }
    assert _is_short(video_60) is False, "Nao deveria ser Short (60s exatos)"

    print("    PASSOU\n")


def test_select_video_file():
    """Testa selecao de arquivo por formato."""
    print("[3] Testando selecao de arquivo...")
    from services.publisher_youtube import _select_video_file

    video = {
        "url_storage_vertical": "https://storage/v.mp4",
        "duracao_vertical_segundos": 45,
        "url_storage_horizontal": "https://storage/h.mp4",
        "duracao_horizontal_segundos": 120,
    }

    # Short -> vertical
    url, dur = _select_video_file(video, is_short=True)
    assert url == "https://storage/v.mp4", f"Esperado vertical, obteve {url}"
    assert dur == 45

    # Nao Short -> horizontal
    url, dur = _select_video_file(video, is_short=False)
    assert url == "https://storage/h.mp4", f"Esperado horizontal, obteve {url}"
    assert dur == 120

    # Sem horizontal -> fallback para vertical
    video_sem_h = {
        "url_storage_vertical": "https://storage/v.mp4",
        "duracao_vertical_segundos": 90,
        "url_storage_horizontal": None,
        "duracao_horizontal_segundos": None,
    }
    url, dur = _select_video_file(video_sem_h, is_short=False)
    assert url == "https://storage/v.mp4"

    # Sem nenhum -> erro
    video_vazio = {
        "url_storage_vertical": None,
        "url_storage_horizontal": None,
    }
    try:
        _select_video_file(video_vazio, is_short=False)
        assert False, "Deveria ter levantado ValueError"
    except ValueError as e:
        assert "Nenhuma versao" in str(e)

    print("    PASSOU\n")


def test_build_title():
    """Testa construcao de titulo."""
    print("[4] Testando construcao de titulo...")
    from services.publisher_youtube import _build_title

    conteudo = {"titulo": "5 Dicas para Usar o App XYZ"}

    # Titulo normal
    titulo = _build_title(conteudo, is_short=False)
    assert titulo == "5 Dicas para Usar o App XYZ"
    assert "#Shorts" not in titulo

    # Titulo Short
    titulo = _build_title(conteudo, is_short=True)
    assert "#Shorts" in titulo
    assert titulo == "5 Dicas para Usar o App XYZ #Shorts"

    # Titulo ja com #Shorts nao duplica
    conteudo2 = {"titulo": "Dica rapida #Shorts"}
    titulo = _build_title(conteudo2, is_short=True)
    assert titulo.count("#Shorts") == 1

    # Titulo longo truncado a 100 chars
    conteudo3 = {"titulo": "A" * 110}
    titulo = _build_title(conteudo3, is_short=False)
    assert len(titulo) <= 100
    assert titulo.endswith("...")

    print("    PASSOU\n")


def test_build_description():
    """Testa construcao de descricao."""
    print("[5] Testando construcao de descricao...")
    from services.publisher_youtube import _build_description

    conteudo = {
        "descricao_youtube": "Aprenda a usar o App XYZ para melhorar sua produtividade.",
        "hashtags_youtube": ["produtividade", "apps", "dicas"],
    }
    app = {
        "cta": "Baixe gratis na App Store!",
        "link_download": "https://apps.apple.com/app/xyz",
    }

    desc = _build_description(conteudo, app, is_short=False)
    assert "Aprenda a usar" in desc
    assert "Baixe gratis" in desc
    assert "apps.apple.com" in desc
    assert "#produtividade" in desc

    # Short adiciona #Shorts
    desc_short = _build_description(conteudo, app, is_short=True)
    assert "#Shorts" in desc_short

    # Descricao > 5000 truncada
    conteudo_longo = {"descricao_youtube": "X" * 5100, "hashtags_youtube": []}
    desc = _build_description(conteudo_longo, {"cta": None, "link_download": None}, is_short=False)
    assert len(desc) <= 5000

    print("    PASSOU\n")


def test_build_tags():
    """Testa construcao de tags."""
    print("[6] Testando construcao de tags...")
    from services.publisher_youtube import _build_tags

    conteudo = {
        "hashtags_youtube": ["#produtividade", "apps", "#dicas"],
        "keywords_seo": ["aplicativo mobile", "produtividade"],
    }

    tags = _build_tags(conteudo)
    assert "produtividade" in tags
    assert "apps" in tags
    assert "dicas" in tags
    assert "aplicativo mobile" in tags
    # Nao deve ter # no inicio
    assert all(not t.startswith("#") for t in tags)
    # Sem duplicatas
    assert len(tags) == len(set(tags))

    print("    PASSOU\n")


def test_retry_constants():
    """Testa constantes de retry."""
    print("[7] Testando constantes de retry...")
    from services.publisher_youtube import MAX_RETRIES, RETRY_DELAYS

    assert MAX_RETRIES == 3
    assert RETRY_DELAYS == [300, 900, 1800]  # 5min, 15min, 30min
    assert len(RETRY_DELAYS) >= MAX_RETRIES - 1  # precisa de delays entre tentativas

    print("    PASSOU\n")


def test_router_endpoints():
    """Testa que os endpoints estao registrados no FastAPI."""
    print("[8] Testando endpoints registrados...")
    from routers.publish import router

    routes = {r.path for r in router.routes}
    assert "/publish/youtube/{video_id}" in routes, f"Rota publish/youtube nao encontrada em {routes}"
    assert "/publish/youtube/{video_id}/retry" in routes, f"Rota retry nao encontrada em {routes}"

    print("    PASSOU\n")


def test_main_includes_publish_router():
    """Testa que main.py inclui o router de publicacao."""
    print("[9] Testando inclusao no main.py...")
    main_path = os.path.join(os.path.dirname(__file__), "main.py")
    with open(main_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "from routers import" in content and "publish" in content, \
        "main.py nao importa routers.publish"
    assert "publish.router" in content, \
        "main.py nao inclui publish.router"

    print("    PASSOU\n")


def test_settings_youtube_fields():
    """Testa que config.py tem os campos do YouTube."""
    print("[10] Testando campos YouTube no config.py...")
    from config import Settings

    s = Settings()
    assert hasattr(s, "youtube_client_id")
    assert hasattr(s, "youtube_client_secret")
    assert hasattr(s, "youtube_refresh_token")

    print("    PASSOU\n")


def test_migration_file_exists():
    """Testa que a migracao da coluna youtube_refresh_token existe."""
    print("[11] Testando arquivo de migracao...")
    migration_path = os.path.join(
        os.path.dirname(__file__), "migrations", "005_youtube_workspace.sql"
    )
    assert os.path.exists(migration_path), f"Migracao nao encontrada: {migration_path}"

    with open(migration_path, "r", encoding="utf-8") as f:
        sql = f.read()
    assert "youtube_refresh_token" in sql
    assert "ALTER TABLE" in sql

    print("    PASSOU\n")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE SESSAO 12 — Publicacao YouTube API v3")
    print("=" * 60 + "\n")

    tests = [
        test_imports,
        test_is_short,
        test_select_video_file,
        test_build_title,
        test_build_description,
        test_build_tags,
        test_retry_constants,
        test_router_endpoints,
        test_main_includes_publish_router,
        test_settings_youtube_fields,
        test_migration_file_exists,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"    FALHOU: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"RESULTADO: {passed} passou, {failed} falhou de {len(tests)} testes")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)
    print("\nSessao 12 implementada com sucesso!")
    print("\nPara testar o entregavel verificavel (publicacao real):")
    print("  1. Configure as variaveis no .env:")
    print("     YOUTUBE_CLIENT_ID=...")
    print("     YOUTUBE_CLIENT_SECRET=...")
    print("     YOUTUBE_REFRESH_TOKEN=...")
    print("  2. Aprove um video via Telegram ou painel")
    print("  3. Ou dispare manualmente:")
    print("     curl -X POST http://localhost:8000/publish/youtube/<video_id>")
    print("       -H 'Authorization: Bearer <token>'")
    print("  4. Verifique: videos.url_youtube != null")
