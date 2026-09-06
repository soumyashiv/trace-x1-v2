"""
Minimal JWT auth for the prototype.

Investigators authenticate against a small in-memory demo user table
(swap for a real user store + password hashing backend in production —
see docs/limitations.md). Passwords are compared using a constant-time
hash check via passlib; secrets and expiry are read from `app.config`.

Role-aware access: 'investigator' can create/run cases; 'admin' can also
view system health/audit logs; 'viewer' is read-only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Demo-only user table. In production this is a database table with
# properly salted/hashed passwords and MFA — not an in-memory dict.
_DEMO_USERS = {
    "demo.investigator": {
        "password_hash": pwd_context.hash("ChangeMe123!"),
        "role": "investigator",
    },
    "demo.admin": {
        "password_hash": pwd_context.hash("ChangeMeAdmin123!"),
        "role": "admin",
    },
}


def authenticate(username: str, password: str) -> Optional[str]:
    """Returns the role string on success, None on failure."""
    user = _DEMO_USERS.get(username)
    if not user or not pwd_context.verify(password, user["password_hash"]):
        return None
    return user["role"]


def create_access_token(subject: str, role: str) -> str:
    secret = settings.require_jwt_secret()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    secret = settings.require_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = decode_token(token)
    return {"username": payload.get("sub"), "role": payload.get("role")}


def require_role(*allowed_roles: str):
    def _dep(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' is not permitted to perform this action",
            )
        return user

    return _dep
