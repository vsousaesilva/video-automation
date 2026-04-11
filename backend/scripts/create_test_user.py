"""
Script para criar/atualizar usuario de teste com senha funcional.
Uso: python scripts/create_test_user.py

Atualiza o usuario 'Carlos Admin' (carlos@appstudio.com) com a senha 'teste123'.
"""

import sys
import os

# Adicionar o diretorio backend ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth_deps import hash_password
from db import get_supabase


def main():
    email = "carlos@appstudio.com"
    senha = "teste123"
    user_id = "d1111111-1111-1111-1111-111111111111"

    senha_hash = hash_password(senha)
    print(f"Hash gerado: {senha_hash}")

    supabase = get_supabase()

    # Atualizar senha do usuario de teste
    result = supabase.table("users").update({
        "senha_hash": senha_hash,
    }).eq("id", user_id).execute()

    if result.data:
        print(f"Senha atualizada para {email}")
        print(f"Use para login:")
        print(f"  email: {email}")
        print(f"  password: {senha}")
    else:
        print(f"Usuario {user_id} nao encontrado. Verifique se a migration 002 foi executada.")


if __name__ == "__main__":
    main()
