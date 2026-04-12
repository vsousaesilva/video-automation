from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Gemini
    gemini_api_key: str = ""

    # Pexels
    pexels_api_key: str = ""

    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Meta / Instagram
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_access_token: str = ""
    meta_instagram_account_id: str = ""

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Resend
    resend_api_key: str = ""

    # Asaas
    asaas_api_key: str = ""
    asaas_base_url: str = "https://sandbox.asaas.com/api/v3"  # sandbox; prod: https://api.asaas.com/v3
    asaas_webhook_token: str = ""

    # App
    frontend_url: str = "http://localhost:5173"
    secret_key: str = "insecure-dev-key-change-me"
    environment: str = "development"
    base_url: str = "http://localhost:8000"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
