"""
Middlewares de segurança: rate limiting, security headers, audit log, billing enforcement.
"""

import logging
import time
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================
# 1. Security Headers Middleware
# ============================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adiciona headers de segurança em todas as respostas."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https://*.supabase.co https://*.asaas.com; "
                "frame-ancestors 'none'"
            )
        return response


# ============================================================
# 2. Audit Log Middleware
# ============================================================

# Rotas e métodos que disparam audit log
AUDIT_ROUTES = {
    ("POST", "/auth/login"): "login",
    ("POST", "/auth/signup"): "signup",
    ("POST", "/auth/forgot-password"): "forgot_password",
    ("POST", "/auth/reset-password"): "reset_password",
    ("PUT", "/auth/change-password"): "change_password",
    ("POST", "/negocios"): "create_negocio",
    ("DELETE", "/negocios"): "delete_negocio",
    ("POST", "/pipeline/trigger"): "trigger_pipeline",
    ("POST", "/publish"): "publish_video",
    ("POST", "/approvals"): "approve_video",
    ("POST", "/billing/checkout"): "billing_checkout",
    ("POST", "/billing/cancel"): "billing_cancel",
    ("POST", "/users"): "invite_user",
    ("DELETE", "/users"): "remove_user",
    ("GET", "/privacy/my-data"): "export_data",
    ("DELETE", "/privacy/my-data"): "delete_data_request",
    ("POST", "/content-ai/generate"): "generate_content_ai",
    ("POST", "/content-ai/use-in-video"): "content_ai_to_video",
}


def _match_audit_route(method: str, path: str) -> str | None:
    """Verifica se a rota deve ser auditada. Suporta prefixos."""
    for (m, route_prefix), action in AUDIT_ROUTES.items():
        if method == m and path.startswith(route_prefix):
            return action
    return None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Registra ações sensíveis na tabela audit_log."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        action = _match_audit_route(request.method, request.url.path)
        if action and response.status_code < 400:
            try:
                self._log_action(request, action, response.status_code)
            except Exception as e:
                logger.warning(f"Falha ao registrar audit log: {e}")

        return response

    def _log_action(self, request: Request, action: str, status_code: int):
        from core.db import get_supabase
        from jose import jwt, JWTError

        # Extrair user/workspace do token (sem validar — é pós-request)
        user_id = None
        workspace_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                payload = jwt.decode(
                    auth_header[7:],
                    settings.secret_key,
                    algorithms=["HS256"],
                    options={"verify_exp": False},
                )
                user_id = payload.get("sub")
                workspace_id = payload.get("workspace_id")
            except JWTError:
                pass

        # IP do cliente
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.client.host if request.client else None

        # Para ações sem token (login, signup, forgot_password), buscar workspace via email
        if not workspace_id and action in ("login", "signup", "forgot_password"):
            # Sem workspace_id não conseguimos inserir (coluna NOT NULL)
            # Pular audit para ações pré-autenticação sem workspace
            return

        if not workspace_id:
            return

        supabase = get_supabase()
        supabase.table("audit_log").insert({
            "workspace_id": workspace_id,
            "user_id": user_id,
            "acao": action,
            "recurso": request.url.path,
            "detalhes": {"method": request.method, "status": status_code},
            "ip_address": client_ip,
            "user_agent": request.headers.get("user-agent", ""),
        }).execute()


# ============================================================
# 3. Billing Enforcement Middleware
# ============================================================

# Rotas que consomem recursos e precisam de verificação de billing
BILLING_CHECKS = {
    ("POST", "/pipeline/trigger"): ("videos_gerados", "max_videos_mes"),
    ("POST", "/negocios"): ("_count_negocios", "max_negocios"),
    ("POST", "/content-ai/generate"): ("conteudos_gerados", "max_conteudos_mes"),
}


class BillingEnforcementMiddleware(BaseHTTPMiddleware):
    """Bloqueia ações quando o workspace atinge o limite do plano."""

    async def dispatch(self, request: Request, call_next):
        check = None
        for (method, prefix), value in BILLING_CHECKS.items():
            if request.method == method and request.url.path.startswith(prefix):
                check = value
                break

        if check:
            blocked = self._check_limit(request, check[0], check[1])
            if blocked:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Limite do plano atingido: {check[1]}. Faça upgrade para continuar."},
                )

        return await call_next(request)

    def _check_limit(self, request: Request, usage_field: str, plan_field: str) -> bool:
        """Retorna True se o limite foi atingido."""
        from core.billing import get_workspace_subscription, get_workspace_usage
        from jose import jwt, JWTError

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return False

        try:
            payload = jwt.decode(
                auth_header[7:],
                settings.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            workspace_id = payload.get("workspace_id")
        except JWTError:
            return False

        if not workspace_id:
            return False

        sub = get_workspace_subscription(workspace_id)
        if not sub or not sub.get("plans"):
            return False

        plan = sub["plans"]
        max_value = plan.get(plan_field)
        if max_value is None:  # None = ilimitado
            return False

        # Contagem especial para negócios
        if usage_field == "_count_negocios":
            from core.db import get_supabase
            supabase = get_supabase()
            result = (
                supabase.table("negocios")
                .select("id", count="exact")
                .eq("workspace_id", workspace_id)
                .execute()
            )
            current = result.count or 0
        else:
            usage = get_workspace_usage(workspace_id)
            current = usage.get(usage_field, 0)

        return current >= max_value
