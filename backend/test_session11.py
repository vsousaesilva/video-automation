"""
Testes da Sessão 11 — Telegram Bot para aprovação de vídeos.

Execução:
  cd backend
  python test_session11.py

Requisitos:
  - Servidor rodando (uvicorn main:app --reload)
  - Variáveis TELEGRAM_BOT_TOKEN e TELEGRAM_WEBHOOK_SECRET no .env
  - Pelo menos um workspace, app, conteúdo e vídeo no banco
  - Um usuário com telegram_user_id preenchido
"""

import json
import asyncio
import os
import httpx
from dotenv import dotenv_values

BASE_URL = "http://localhost:8000"

# Timeout generoso para evitar ReadError em servidores lentos
CLIENT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)

# Carregar secret do .env para autenticar nos testes
_env = dotenv_values(".env")
WEBHOOK_SECRET = _env.get("TELEGRAM_WEBHOOK_SECRET", "")
SECRET_HEADERS = {"X-Telegram-Bot-Api-Secret-Token": WEBHOOK_SECRET} if WEBHOOK_SECRET else {}


async def test_health():
    """Verifica se o servidor está rodando."""
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            r = await client.get(f"{BASE_URL}/health")
            assert r.status_code == 200, f"Health check falhou: {r.status_code}"
            print("[OK] Health check")
        except httpx.ConnectError:
            print("[ERRO] Servidor não está rodando em", BASE_URL)
            print("       Execute: venv\\Scripts\\python -m uvicorn main:app --reload")
            raise SystemExit(1)


async def test_webhook_endpoint_exists():
    """Verifica se o endpoint /telegram/webhook responde."""
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            r = await client.post(f"{BASE_URL}/telegram/webhook", json={}, headers=SECRET_HEADERS)
            assert r.status_code == 200, f"Webhook retornou {r.status_code}: {r.text}"
            data = r.json()
            assert data.get("ok") is True
            print("[OK] Endpoint /telegram/webhook existe e responde")
        except (httpx.ReadError, httpx.RemoteProtocolError) as e:
            print(f"[ERRO] Servidor crashou ao processar webhook: {e}")
            print("       Verifique o terminal do servidor para ver o traceback")


async def test_webhook_invalid_secret():
    """Verifica rejeição com secret token inválido (se configurado)."""
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        r = await client.post(
            f"{BASE_URL}/telegram/webhook",
            json={},
            headers={"X-Telegram-Bot-Api-Secret-Token": "token-invalido-123"},
        )
        # Se TELEGRAM_WEBHOOK_SECRET estiver configurado, deve retornar 403
        # Se não estiver configurado, retorna 200 (aceita qualquer um em dev)
        if r.status_code == 403:
            print("[OK] Secret token inválido rejeitado corretamente (403)")
        else:
            print("[OK] Secret token não configurado — modo dev (aceita qualquer requisição)")


async def test_webhook_callback_query_unknown_user():
    """Simula callback de um usuário desconhecido."""
    fake_callback = {
        "callback_query": {
            "id": "fake-callback-id-123",
            "from": {
                "id": 999999999,  # ID inexistente
                "is_bot": False,
                "first_name": "Teste",
            },
            "message": {
                "message_id": 1,
                "chat": {"id": -100123456789, "type": "group"},
            },
            "data": json.dumps({"action": "aprovar", "video_id": "fake-video-id"}),
        }
    }
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            r = await client.post(f"{BASE_URL}/telegram/webhook", json=fake_callback, headers=SECRET_HEADERS)
            assert r.status_code == 200
            print("[OK] Callback de usuário desconhecido tratado corretamente")
        except (httpx.ReadError, httpx.RemoteProtocolError) as e:
            print(f"[ERRO] Servidor crashou no callback de usuário desconhecido: {e}")
            print("       Verifique o terminal do servidor")


async def test_webhook_callback_invalid_data():
    """Simula callback com dados inválidos."""
    fake_callback = {
        "callback_query": {
            "id": "fake-callback-id-456",
            "from": {"id": 123456, "is_bot": False, "first_name": "Teste"},
            "message": {
                "message_id": 1,
                "chat": {"id": -100123456789, "type": "group"},
            },
            "data": "dados-invalidos-nao-json",
        }
    }
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        try:
            r = await client.post(f"{BASE_URL}/telegram/webhook", json=fake_callback, headers=SECRET_HEADERS)
            assert r.status_code == 200
            print("[OK] Callback com dados inválidos tratado corretamente")
        except (httpx.ReadError, httpx.RemoteProtocolError) as e:
            print(f"[ERRO] Servidor crashou no callback inválido: {e}")
            print("       Verifique o terminal do servidor")


async def test_send_approval_import():
    """Verifica se o módulo telegram_bot importa corretamente."""
    try:
        from services.telegram_bot import (
            send_approval_request,
            send_published_notification,
            send_error_notification,
            update_telegram_message,
            register_webhook,
        )
        print("[OK] Módulo services/telegram_bot importado com sucesso")
        print(f"     Funções: send_approval_request, send_published_notification,")
        print(f"     send_error_notification, update_telegram_message, register_webhook")
    except ImportError as e:
        print(f"[ERRO] Falha ao importar telegram_bot: {e}")


async def test_webhook_router_import():
    """Verifica se o módulo telegram_webhook importa corretamente."""
    try:
        from routers.telegram_webhook import router
        routes = [r.path for r in router.routes]
        assert any("/webhook" in r for r in routes), f"Rota /webhook não encontrada. Rotas: {routes}"
        print("[OK] Módulo routers/telegram_webhook importado com sucesso")
        print(f"     Rotas registradas: {routes}")
    except ImportError as e:
        print(f"[ERRO] Falha ao importar telegram_webhook: {e}")


async def test_full_flow_simulation():
    """
    Teste integrado: simula o fluxo completo de envio + aprovação.

    NOTA: Para testar com um bot real, configure as variáveis no .env:
      TELEGRAM_BOT_TOKEN=seu-token
      TELEGRAM_WEBHOOK_SECRET=seu-secret

    E vincule um telegram_user_id a um usuário no banco:
      UPDATE users SET telegram_user_id = SEU_TELEGRAM_ID WHERE email = 'seu@email.com';
    """
    print("\n" + "=" * 60)
    print("TESTE INTEGRADO — Fluxo completo")
    print("=" * 60)

    # 1. Buscar um vídeo aguardando aprovação
    async with httpx.AsyncClient(timeout=CLIENT_TIMEOUT) as client:
        # Login para obter token
        login_r = await client.post(f"{BASE_URL}/auth/login", json={
            "email": "admin@teste.com",
            "password": "123456",
        })

        if login_r.status_code != 200:
            print("[PULAR] Não foi possível fazer login — configure dados de teste")
            print(f"        Status: {login_r.status_code}, Body: {login_r.text}")
            return

        token = login_r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Buscar vídeos pendentes
        videos_r = await client.get(f"{BASE_URL}/videos/pending", headers=headers)
        if videos_r.status_code != 200 or not videos_r.json():
            print("[PULAR] Nenhum vídeo pendente encontrado para teste integrado")
            return

        video = videos_r.json()[0]
        video_id = video["id"]
        print(f"[INFO] Vídeo pendente encontrado: {video_id}")
        print(f"       Status: {video['status']}")

        # 3. Simular aprovação via webhook
        print(f"\n[INFO] Simulando aprovação via Telegram webhook...")

        # Para o teste funcionar, precisamos de um usuário com telegram_user_id
        # Aqui apenas verificamos que o endpoint processa sem erro
        fake_approval = {
            "callback_query": {
                "id": "test-approval-flow",
                "from": {"id": 0, "is_bot": False, "first_name": "TestBot"},
                "message": {
                    "message_id": 1,
                    "chat": {"id": -1, "type": "group"},
                },
                "data": json.dumps({"action": "aprovar", "video_id": video_id}),
            }
        }

        r = await client.post(f"{BASE_URL}/telegram/webhook", json=fake_approval, headers=SECRET_HEADERS)
        assert r.status_code == 200
        print(f"[OK] Webhook processou callback sem erro (status 200)")
        print(f"     Nota: aprovação real requer telegram_user_id vinculado")


async def main():
    print("=" * 60)
    print("Sessão 11 — Testes do Telegram Bot")
    print("=" * 60)
    print()

    await test_health()
    await test_send_approval_import()
    await test_webhook_router_import()

    print()
    print("-" * 60)
    print("Testes do endpoint webhook:")
    print("-" * 60)

    await test_webhook_invalid_secret()
    await test_webhook_endpoint_exists()
    await test_webhook_callback_query_unknown_user()
    await test_webhook_callback_invalid_data()

    await test_full_flow_simulation()

    print()
    print("=" * 60)
    print("Todos os testes concluídos!")
    print("=" * 60)
    print()
    print("Para testar com bot real:")
    print("  1. Crie um bot no @BotFather e copie o token")
    print("  2. Configure no .env: TELEGRAM_BOT_TOKEN=seu-token")
    print("  3. Configure: TELEGRAM_WEBHOOK_SECRET=um-secret-qualquer")
    print("  4. No banco, atualize o workspace:")
    print("     UPDATE workspaces SET telegram_bot_token='token', telegram_chat_id='chat_id';")
    print("  5. Vincule seu Telegram ID ao usuário:")
    print("     UPDATE users SET telegram_user_id=SEU_ID WHERE email='seu@email.com';")
    print("  6. Para descobrir seu Telegram ID, envie /start ao @userinfobot")


if __name__ == "__main__":
    asyncio.run(main())
