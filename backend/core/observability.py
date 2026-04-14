"""
Observabilidade: Sentry, structured logging (JSON) e correlation IDs.

Tudo fica no-op quando as dependencias opcionais nao estao instaladas ou quando
`SENTRY_DSN` nao esta configurado, para nao travar ambientes de dev.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import get_settings

# Context var para propagar correlation_id entre handlers async e logs
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def set_correlation_id(value: str | None) -> None:
    _correlation_id.set(value)


# ============================================================
# Structured JSON logging
# ============================================================

_STD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName", "asctime",
}


class JsonFormatter(logging.Formatter):
    """Formatador que emite uma linha JSON por registro."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        cid = get_correlation_id()
        if cid:
            payload["correlation_id"] = cid

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Extras customizados via logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key in _STD_ATTRS or key.startswith("_"):
                continue
            try:
                json.dumps(value)
                payload[key] = value
            except TypeError:
                payload[key] = repr(value)

        return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    """Configura root logger de acordo com settings."""
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    if settings.environment == "production":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    # Uvicorn tem loggers proprios — deixar propagar para o root
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ============================================================
# Sentry
# ============================================================

_sentry_ready = False


def init_sentry() -> bool:
    """Inicia Sentry se DSN configurado e SDK disponivel. Retorna True em sucesso."""
    global _sentry_ready
    settings = get_settings()
    dsn = getattr(settings, "sentry_dsn", "") or ""
    if not dsn:
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logging.getLogger(__name__).warning(
            "SENTRY_DSN definido mas sentry-sdk nao instalado — instale sentry-sdk[fastapi]"
        )
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        release=getattr(settings, "app_version", "unknown"),
        traces_sample_rate=0.1 if settings.environment == "production" else 0.0,
        send_default_pii=False,
        integrations=[FastApiIntegration(), StarletteIntegration()],
    )
    _sentry_ready = True
    return True


def sentry_is_ready() -> bool:
    return _sentry_ready


# ============================================================
# Correlation ID middleware
# ============================================================

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Adiciona X-Correlation-ID em toda requisicao/resposta e loga request completion."""

    async def dispatch(self, request: Request, call_next) -> Response:
        cid = request.headers.get(CORRELATION_HEADER) or uuid.uuid4().hex
        set_correlation_id(cid)

        start = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logging.getLogger("request").exception(
                "request_failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )
            set_correlation_id(None)
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[CORRELATION_HEADER] = cid

        # Log apenas rotas nao-health para reduzir ruido
        if not request.url.path.startswith("/health"):
            logging.getLogger("request").info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

        set_correlation_id(None)
        return response
