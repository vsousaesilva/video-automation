"""
Criptografia de credenciais de APIs externas usando Fernet (AES-128-CBC).
Chave derivada do secret_key da aplicação via PBKDF2.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from core.config import get_settings


def _derive_key(secret: str) -> bytes:
    """Deriva uma chave Fernet de 32 bytes a partir do secret_key."""
    key = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        b"usina-do-tempo-fernet-salt",
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(key)


def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(_derive_key(settings.secret_key))


def encrypt_value(plaintext: str) -> str:
    """Criptografa um valor e retorna string base64."""
    if not plaintext:
        return ""
    f = _get_fernet()
    return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    """Descriptografa um valor. Se não for Fernet válido, retorna o valor original (plaintext legado)."""
    if not ciphertext:
        return ""
    f = _get_fernet()
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception):
        # Fallback: se não é Fernet, assume que é plaintext legado
        return ciphertext


# --- Helpers para salvar credenciais criptografadas no workspace ---

ENCRYPTED_FIELDS = [
    "youtube_client_secret_enc",
    "youtube_refresh_token_enc",
    "meta_app_secret_enc",
    "meta_access_token_enc",
    "google_ads_refresh_token_enc",
    "tiktok_ads_access_token_enc",
]


def encrypt_workspace_credentials(data: dict) -> dict:
    """
    Recebe dict com campos de credenciais e retorna com valores criptografados.
    Campos que terminam em '_enc' são criptografados automaticamente.

    Uso:
        update_data = encrypt_workspace_credentials({
            "youtube_refresh_token_enc": "meu-token-secreto",
            "meta_access_token_enc": "outro-token",
        })
        supabase.table("workspaces").update(update_data).eq("id", ws_id).execute()
    """
    result = {}
    for key, value in data.items():
        if key in ENCRYPTED_FIELDS and value:
            result[key] = encrypt_value(value)
        else:
            result[key] = value
    return result
