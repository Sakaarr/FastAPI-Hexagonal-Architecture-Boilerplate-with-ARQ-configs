"""
╔══════════════════════════════════════════════════════════════╗
║  INFRASTRUCTURE: JWT Token Utilities                         ║
║                                                              ║
║  Creates and verifies JWT access tokens.                     ║
║                                                              ║
║  JWT Structure:                                              ║
║  ┌─────────┐  ┌─────────────────┐  ┌──────────┐              ║
║  │ HEADER  │. │    PAYLOAD      │. │SIGNATURE │              ║
║  │ alg,typ │  │ sub,exp,iat,... │  │ HMAC     │              ║
║  └─────────┘  └─────────────────┘  └──────────┘              ║
╚══════════════════════════════════════════════════════════════╝
"""

from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.infrastructure.config import get_settings


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload to encode (typically {"sub": user_id})
        expires_delta: Custom expiry time (default: from settings)

    Returns:
        Encoded JWT string

    LEARNING POINT:
    ─────────────────
    The token contains:
    - sub: Subject (user ID) — identifies WHO this token belongs to
    - exp: Expiry timestamp — token auto-expires after this time
    - iat: Issued at — when the token was created
    - type: Token type — "access" (could also be "refresh")

    The token is SIGNED with a secret key using HMAC-SHA256.
    This means:
    - Anyone can READ the payload (it's just base64)
    - But only the server can VERIFY it wasn't tampered with
    - NEVER put sensitive data (passwords, etc.) in the payload
    """
    settings = get_settings()

    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_expiry_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })

    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict | None:
    """
    Decode and verify a JWT access token.

    Returns the payload dict if valid, None if invalid/expired.

    LEARNING POINT:
    ─────────────────
    python-jose handles:
    - Signature verification (was the token signed by US?)
    - Expiry checking (has the token expired?)
    - Algorithm validation (is it using the expected algorithm?)

    If ANY of these fail, JWTError is raised → we return None.
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
