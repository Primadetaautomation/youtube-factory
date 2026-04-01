"""Simple JWT authentication for YouTube Factory."""

import os
import time
import jwt

SECRET_KEY = os.getenv("APP_SECRET_KEY", "youtube-factory-default-secret-change-me")
TOKEN_EXPIRY = 86400 * 7  # 7 days


def verify_credentials(email: str, password: str) -> bool:
    """Check email/password against env vars."""
    expected_email = os.getenv("APP_EMAIL", "")
    expected_password = os.getenv("APP_PASSWORD", "")
    if not expected_email or not expected_password:
        return False
    return email == expected_email and password == expected_password


def create_token(email: str) -> str:
    """Create a JWT token for the given email."""
    payload = {
        "email": email,
        "exp": int(time.time()) + TOKEN_EXPIRY,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def verify_token(token: str) -> str | None:
    """Verify a JWT token, return email or None."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("email")
    except (jwt.InvalidTokenError, jwt.ExpiredSignatureError):
        return None
