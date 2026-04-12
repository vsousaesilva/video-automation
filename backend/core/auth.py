from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import bcrypt

from core.config import get_settings
from core.db import get_supabase

settings = get_settings()

security = HTTPBearer()

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_invite_token(email: str, workspace_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=3)
    return jwt.encode(
        {"email": email, "workspace_id": workspace_id, "exp": expire, "type": "invite"},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_token(token: str, expected_type: str = "access") -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != expected_type:
            raise HTTPException(status_code=401, detail="Tipo de token inválido")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = decode_token(credentials.credentials, expected_type="access")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")

    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("id", user_id).eq("ativo", True).execute()

    if not result.data:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou desativado")

    return result.data[0]


def require_role(allowed_roles: list[str]):
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["papel"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso restrito aos papéis: {', '.join(allowed_roles)}",
            )
        return current_user
    return role_checker
