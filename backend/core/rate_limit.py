"""
Rate limiting usando slowapi + proteção brute-force para login.
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================
# Rate limiter global (SlowAPI)
# ============================================================

def _get_identifier(request: Request) -> str:
    """Identifica request por workspace_id (se autenticado) ou IP."""
    from jose import jwt, JWTError
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = jwt.decode(
                auth_header[7:],
                settings.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            ws = payload.get("workspace_id")
            if ws:
                return f"ws:{ws}"
        except JWTError:
            pass
    return get_remote_address(request)


def _get_storage_uri() -> str:
    """Usa Redis se disponível, senão fallback para memória."""
    try:
        import redis
        r = redis.from_url(settings.redis_url, socket_connect_timeout=1)
        r.ping()
        logger.info("Rate limiter usando Redis")
        return settings.redis_url
    except Exception:
        logger.info("Rate limiter usando memória (Redis indisponível)")
        return "memory://"


limiter = Limiter(
    key_func=_get_identifier,
    default_limits=["60/minute"],
    storage_uri=_get_storage_uri(),
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Handler customizado para 429."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Limite de requisições excedido. Tente novamente em instantes."},
    )


# ============================================================
# Brute-force protection (login)
# ============================================================

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def check_login_lockout(user: dict) -> bool:
    """Retorna True se a conta está bloqueada."""
    locked_until = user.get("locked_until")
    if not locked_until:
        return False
    if isinstance(locked_until, str):
        locked_until = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
    return datetime.now(timezone.utc) < locked_until


def record_failed_login(user_id: str):
    """Incrementa tentativas falhas. Bloqueia após MAX_LOGIN_ATTEMPTS."""
    from core.db import get_supabase
    supabase = get_supabase()

    result = supabase.table("users").select("login_attempts").eq("id", user_id).execute()
    if not result.data:
        return

    attempts = (result.data[0].get("login_attempts") or 0) + 1
    update_data = {"login_attempts": attempts}

    if attempts >= MAX_LOGIN_ATTEMPTS:
        update_data["locked_until"] = (
            datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
        ).isoformat()
        logger.warning(f"Conta bloqueada por brute-force: user_id={user_id}, attempts={attempts}")

    supabase.table("users").update(update_data).eq("id", user_id).execute()


def reset_login_attempts(user_id: str):
    """Reseta contadores após login bem-sucedido."""
    from core.db import get_supabase
    supabase = get_supabase()
    supabase.table("users").update({
        "login_attempts": 0,
        "locked_until": None,
    }).eq("id", user_id).execute()
