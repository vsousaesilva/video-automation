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

    # Google Ads
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_developer_token: str = ""
    google_ads_login_customer_id: str = ""  # MCC (manager) opcional
    google_ads_api_version: str = "v17"

    # TikTok Ads (Marketing API)
    tiktok_ads_app_id: str = ""
    tiktok_ads_app_secret: str = ""
    tiktok_ads_api_base: str = "https://business-api.tiktok.com/open_api/v1.3"

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    # Resend
    resend_api_key: str = ""

    # Asaas
    asaas_api_key: str = ""
    asaas_base_url: str = "https://sandbox.asaas.com/api/v3"  # sandbox; prod: https://api.asaas.com/v3
    asaas_webhook_token: str = ""

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"

    # Flower (monitoramento Celery)
    flower_user: str = ""
    flower_password: str = ""

    # App
    frontend_url: str = "http://localhost:5173"
    secret_key: str = "insecure-dev-key-change-me"
    environment: str = "development"
    base_url: str = "http://localhost:8000"
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
