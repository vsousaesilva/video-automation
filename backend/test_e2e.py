"""
Teste End-to-End — Sessão 17
Valida o pipeline completo: workspace → app → conteúdo → vídeo → aprovação.

Uso:
    python test_e2e.py [BASE_URL]

Exemplo local:
    python test_e2e.py http://localhost:8000

Exemplo produção:
    python test_e2e.py https://video-automation-api.onrender.com
"""

import sys
import time
import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
TIMEOUT = 180  # 3 min para operações lentas (geração de vídeo)


def log(step, msg, ok=True):
    status = "OK" if ok else "FALHA"
    print(f"  [{status}] Passo {step}: {msg}")


def main():
    client = httpx.Client(base_url=BASE_URL, timeout=30)

    print(f"\n{'='*60}")
    print(f"  TESTE END-TO-END — Video Automation Platform")
    print(f"  Base URL: {BASE_URL}")
    print(f"{'='*60}\n")

    # --- Passo 0: Health check ---
    print("0. Health check...")
    try:
        r = client.get("/health")
        assert r.status_code == 200
        log(0, "Backend acessível")
    except Exception as e:
        log(0, f"Backend inacessível: {e}", ok=False)
        print("\n  Verifique se o backend está rodando.")
        return

    # --- Passo 1: Criar workspace + admin ---
    print("\n1. Criando workspace e usuário admin...")
    ts = int(time.time())
    ws_data = {
        "nome": f"E2E Test Workspace {ts}",
        "segmento": "tecnologia",
        "tom_voz": "profissional",
        "idioma": "pt-BR",
        "admin_nome": "Admin E2E",
        "admin_email": f"e2e_{ts}@test.local",
        "admin_senha": "teste123456",
    }
    r = client.post("/workspaces", json=ws_data)
    if r.status_code == 201:
        tokens = r.json()
        access_token = tokens["access_token"]
        client.headers["Authorization"] = f"Bearer {access_token}"
        log(1, f"Workspace criado. E-mail: {ws_data['admin_email']}")
    else:
        log(1, f"Erro ao criar workspace: {r.status_code} - {r.text}", ok=False)
        return

    # --- Passo 2: Cadastrar app ---
    print("\n2. Cadastrando app de teste...")
    current_hour = time.localtime().tm_hour
    test_hour = (current_hour + 1) % 24  # próxima hora
    app_data = {
        "nome": f"TestApp E2E {ts}",
        "categoria": "saude",
        "descricao": "App de teste para validação do pipeline end-to-end. Oferece treinos personalizados com IA.",
        "publico_alvo": "pessoas 25-40 interessadas em saúde",
        "funcionalidades": ["treinos personalizados", "monitoramento de progresso", "dieta inteligente"],
        "diferenciais": ["IA adaptativa", "planos gratuitos"],
        "cta": "Baixe grátis agora",
        "link_download": "https://example.com/download",
        "plataformas": ["instagram", "youtube"],
        "formato_youtube": "ambos",
        "frequencia": "diaria",
        "horario_disparo": test_hour,
        "tom_voz": "motivacional",
        "keywords": ["saúde", "fitness", "treino", "IA"],
    }
    r = client.post("/apps", json=app_data)
    if r.status_code == 201:
        app = r.json()
        app_id = app["id"]
        log(2, f"App criado: {app['nome']} (id: {app_id[:8]}..., disparo: {test_hour}h)")
    else:
        log(2, f"Erro ao criar app: {r.status_code} - {r.text}", ok=False)
        return

    # --- Passo 3: Verificar listagem ---
    print("\n3. Verificando listagem de apps...")
    r = client.get("/apps")
    apps = r.json()
    found = any(a["id"] == app_id for a in apps)
    log(3, f"Apps no workspace: {len(apps)}. App de teste encontrado: {found}", ok=found)

    # --- Passo 4: Verificar schedule ---
    print("\n4. Verificando schedule do dia...")
    r = client.get("/apps/schedule/today")
    schedule = r.json()
    log(4, f"Apps agendados para hoje: {len(schedule)}")

    # --- Passo 5: Disparar pipeline manualmente ---
    print(f"\n5. Disparando pipeline manualmente (hora={test_hour})...")
    r = client.post("/pipeline/trigger", json={"hora_atual": test_hour}, timeout=TIMEOUT)
    if r.status_code == 200:
        result = r.json()
        triggered = result.get("apps_triggered", [])
        log(5, f"Pipeline disparado. Apps processados: {triggered}")
    else:
        log(5, f"Erro no pipeline: {r.status_code} - {r.text}", ok=False)
        print("  (Isso pode ser normal se dependências externas não estão configuradas)")

    # --- Passo 6: Verificar conteúdo gerado ---
    print("\n6. Verificando conteúdo gerado...")
    time.sleep(2)
    r = client.get(f"/apps/{app_id}/history")
    history = r.json()
    if history:
        video = history[0]
        log(6, f"Vídeos encontrados: {len(history)}. Status do mais recente: {video.get('status')}")

        video_id = video["id"]

        # --- Passo 7: Verificar detalhes do vídeo ---
        print("\n7. Verificando detalhes do vídeo...")
        r = client.get(f"/videos/{video_id}")
        if r.status_code == 200:
            detail = r.json()
            has_vertical = bool(detail.get("url_storage_vertical"))
            has_horizontal = bool(detail.get("url_storage_horizontal"))
            has_content = bool(detail.get("conteudo"))
            log(7, f"Vertical: {has_vertical}, Horizontal: {has_horizontal}, Conteúdo: {has_content}")

            if has_content:
                c = detail["conteudo"]
                print(f"       Título: {c.get('titulo', 'N/A')}")
                print(f"       Tipo: {c.get('tipo_conteudo', 'N/A')}")
        else:
            log(7, f"Erro ao buscar detalhes: {r.status_code}", ok=False)

        # --- Passo 8: Verificar vídeos pendentes ---
        print("\n8. Verificando fila de aprovação...")
        r = client.get("/videos/pending")
        pending = r.json()
        pending_for_app = [v for v in pending if v["app_id"] == app_id]
        log(8, f"Vídeos pendentes total: {len(pending)}, para este app: {len(pending_for_app)}")

        # --- Passo 9: Aprovar pelo painel (se pendente) ---
        if pending_for_app:
            print("\n9. Aprovando vídeo pelo painel...")
            vid = pending_for_app[0]["id"]
            r = client.post(f"/approvals/{vid}/approve", timeout=TIMEOUT)
            if r.status_code == 200:
                log(9, f"Vídeo aprovado: {r.json().get('message')}")
            else:
                log(9, f"Erro ao aprovar: {r.status_code} - {r.text}", ok=False)

            # --- Passo 10: Verificar status final ---
            print("\n10. Verificando status final...")
            time.sleep(5)
            r = client.get(f"/videos/{vid}")
            if r.status_code == 200:
                final = r.json()
                log(10, f"Status final: {final.get('status')}")
                if final.get("url_youtube"):
                    print(f"        YouTube: {final['url_youtube']}")
                if final.get("url_instagram"):
                    print(f"        Instagram: {final['url_instagram']}")
            else:
                log(10, "Não foi possível verificar status final", ok=False)
        else:
            print("\n9-10. Sem vídeos pendentes para aprovar (pipeline pode ter falhado).")
    else:
        log(6, "Nenhum vídeo encontrado no histórico. Pipeline pode ter falhado.", ok=False)
        print("  Verifique se GEMINI_API_KEY está configurada e se o Supabase está acessível.")

    # --- Resumo ---
    print(f"\n{'='*60}")
    print(f"  TESTE CONCLUÍDO")
    print(f"  Workspace: {ws_data['nome']}")
    print(f"  Admin: {ws_data['admin_email']} / {ws_data['admin_senha']}")
    print(f"  App: {app_data['nome']} (horário: {test_hour}h)")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
