"""Anonymous device registration and signed device tokens (spec §6).

No sign-up wall in v1: POST /v1/devices mints a device_id and a signed JWT.
Verification is stateless, so tokens survive server restarts.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional
from uuid import uuid4

import jwt
from fastapi import Header, HTTPException, Request, status

from .config import Settings

_ALGORITHM = "HS256"


def issue_device_token(settings: Settings) -> tuple[str, str, datetime]:
    """Mint a new device identity. Returns (device_id, token, expires_at)."""
    device_id = uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.token_ttl_days)
    token = jwt.encode(
        {
            "sub": device_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(expires_at.timestamp()),
        },
        settings.secret_key,
        algorithm=_ALGORITHM,
    )
    return device_id, token, expires_at


def verify_device_token(token: str, settings: Settings) -> str:
    """Return the device_id encoded in a token, or raise 401."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[_ALGORITHM])
    except jwt.InvalidTokenError:
        raise _unauthorized("Invalid or expired device token")
    device_id = payload.get("sub")
    if not device_id:
        raise _unauthorized("Malformed device token")
    return device_id


async def require_device(
    request: Request,
    authorization: Annotated[Optional[str], Header()] = None,
) -> str:
    """FastAPI dependency: authenticate the Bearer device token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise _unauthorized("Missing Bearer device token")
    return verify_device_token(
        authorization[len("Bearer "):], request.app.state.settings
    )


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthorized", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )
