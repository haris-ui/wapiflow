import uuid
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

logger = logging.getLogger("wapiflow.tenant_middleware")


def decode_jwt_token(token: str) -> Optional[dict]:
    """
    Validate and decode a Supabase or application JWT token.
    Extracts sub (UUID) and email.
    """
    settings = get_settings()
    secrets = [settings.SUPABASE_JWT_SECRET, settings.SECRET_KEY]

    for secret in secrets:
        if not secret:
            continue
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[settings.ALGORITHM],
                options={"verify_aud": False},
            )
            sub = payload.get("sub")
            if sub:
                return {
                    "id": uuid.UUID(str(sub)),
                    "email": payload.get("email", ""),
                    "raw_payload": payload,
                }
        except (JWTError, ValueError):
            continue

    return None


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that parses JWT tokens from the Authorization header and attaches
    user metadata to request.state.user for downstream tenant resolution.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request.state.user = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            user_info = decode_jwt_token(token)
            if user_info:
                request.state.user = user_info

        response = await call_next(request)
        return response
