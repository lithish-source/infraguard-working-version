"""JWT + password hashing security utilities."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import bcrypt
import jwt

from app.core.config import settings


# ----- Password hashing (bcrypt direct — robust against passlib version drift) -----
def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")
    # bcrypt truncates at 72 bytes; we hash-sha256 first for arbitrary length
    if len(pw_bytes) > 72:
        import hashlib
        pw_bytes = hashlib.sha256(pw_bytes).digest()
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pw_bytes = plain.encode("utf-8")
        if len(pw_bytes) > 72:
            import hashlib
            pw_bytes = hashlib.sha256(pw_bytes).digest()
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


# ----- JWT tokens -----
def _create_token(
    subject: Union[str, int],
    expires_delta: timedelta,
    token_type: str = "access",
    extra: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": now + expires_delta,
        "type": token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    user_id: Union[str, int], role: str, extra: Optional[dict] = None
) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
        extra={"role": role, **(extra or {})},
    )


def create_refresh_token(user_id: Union[str, int]) -> str:
    return _create_token(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT. Raises jwt.PyJWTError on invalid tokens."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
