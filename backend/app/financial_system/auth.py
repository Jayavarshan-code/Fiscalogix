import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session


ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hours

_INSECURE_FALLBACK = "CHANGE_ME_SET_JWT_SECRET_KEY_ENV_VAR"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _INSECURE_FALLBACK)

if SECRET_KEY == _INSECURE_FALLBACK:
    import logging as _logging
    _logging.getLogger(__name__).critical(
        "SECURITY: JWT_SECRET_KEY is not set (using insecure default). "
        "Tokens can be forged. "
        "Set JWT_SECRET_KEY in your environment before accepting traffic. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
    if os.environ.get("ALLOW_INSECURE_JWT", "").lower() not in ("1", "true"):
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is not set. "
            "Set ALLOW_INSECURE_JWT=true to override in local development only."
        )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    FastAPI dependency that validates the JWT on every protected route.
    Raises 401 if the token is missing, expired, or tampered with.

    Usage:
        @router.get("/protected")
        def my_route(user=Depends(get_current_user)):
            tenant_id = user["tenant_id"]
            perms     = user.get("permissions", {})
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exc
    if payload.get("sub") is None:
        raise credentials_exc
    return payload


def require_permission(permission: str):
    """
    Factory dependency that gates a route behind a specific permission key.

    Re-fetches the user's role from the DB on every call so role changes
    (demotion, suspension) take effect immediately — not after the 24-hour
    token expiry.  Adds one DB query per protected request; acceptable cost
    for write/admin operations.

    Usage:
        @router.post("/execution/action")
        def execute(user=Depends(require_permission("can_execute_actions"))):
            ...
    """
    def _check(
        user: dict = Depends(get_current_user),
        db: Session = Depends(_get_db),
    ):
        from setup_db import User, Role
        db_user = db.query(User).filter(User.id == user.get("user_id")).first()
        if db_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found.",
            )
        role       = db.query(Role).filter(Role.id == db_user.role_id).first()
        live_perms = role.permissions if role else {}
        if not (live_perms.get("is_admin") or live_perms.get(permission)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required.",
            )
        return user
    return _check


def _get_db():
    """Local import avoids circular dependency with app.Db.connections."""
    from app.Db.connections import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
