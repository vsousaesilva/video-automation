"""
Teste da Sessão 10 — Validação + Notificação.
Insere um vídeo de teste no banco e dispara a validação e notificação.
"""

from db import get_supabase
from services.video_validator import validate_video, update_video_status_error, update_video_status_approved
from services.notifier import notify_approval_needed, notify_error

# IDs do teste (substituir se necessário)
APP_ID = "6b88fb5d-d2ca-4f22-9e93-c57cb64b1c64"
CONTEUDO_ID = "f722a7d8-ab88-400f-b39a-f728bc3362bd"


def main():
    supabase = get_supabase()

    # 1. Buscar app
    app = supabase.table("apps").select("*").eq("id", APP_ID).execute().data[0]
    print(f"[OK] App encontrado: {app['nome']}")

    # 2. Inserir vídeo de teste simulando geração bem-sucedida
    video_data = {
        "conteudo_id": CONTEUDO_ID,
        "app_id": APP_ID,
        "url_storage_vertical": None,       # sem arquivo real — vai falhar na validação
        "duracao_vertical_segundos": 45,
        "url_storage_horizontal": None,
        "duracao_horizontal_segundos": 120,
        "tamanho_bytes_total": 5_000_000,
        "status": "processando",
    }
    video_result = supabase.table("videos").insert(video_data).execute()
    video = video_result.data[0]
    video_id = video["id"]
    print(f"[OK] Vídeo de teste inserido: {video_id}")

    # 3. Executar validação (vai falhar pois não há arquivos reais)
    print("\n--- Teste 1: Vídeo INVÁLIDO (sem arquivos) ---")
    validation = validate_video(video, app)
    print(f"  is_valid: {validation.is_valid}")
    print(f"  errors: {validation.errors}")

    if not validation.is_valid:
        update_video_status_error(video_id, validation.errors)
        print(f"  [OK] Status atualizado para 'erro_validacao'")

        # Buscar admins para notificação (usar e-mail da conta Resend para teste)
        admins = [{"email": "suporte@usinadotempo.com.br", "papel": "admin"}]
        print(f"  Admins para notificar: {[a['email'] for a in admins]}")

        notify_error(video, app, admins, "; ".join(validation.errors))
        print(f"  [OK] E-mail de erro enviado!")

    # 4. Agora simular um vídeo VÁLIDO (atualizar status manualmente)
    print("\n--- Teste 2: Vídeo VÁLIDO (simulado) ---")
    supabase.table("videos").update({
        "status": "aguardando_aprovacao",
    }).eq("id", video_id).execute()
    print(f"  [OK] Status atualizado para 'aguardando_aprovacao'")

    # Usar e-mail da conta Resend para teste
    editors = [{"email": "suporte@usinadotempo.com.br", "papel": "editor"}]
    print(f"  Editores para notificar: {[e['email'] for e in editors]}")

    notify_approval_needed(video, app, editors)
    print(f"  [OK] E-mail de aprovação enviado!")

    # 5. Verificar status final
    final = supabase.table("videos").select("id, status, erro_msg").eq("id", video_id).execute().data[0]
    print(f"\n--- Resultado final ---")
    print(f"  Video ID: {final['id']}")
    print(f"  Status:   {final['status']}")
    print(f"  Erro msg: {final.get('erro_msg', '—')}")
    print(f"\nVerifique seu e-mail (suporte@usinadotempo.com.br) para os 2 e-mails enviados!")


if __name__ == "__main__":
    main()