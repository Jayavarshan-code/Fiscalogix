import os
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

# SECRET_KEY must be set via environment variable in production.
# The fallback below is intentionally weak so it's obvious when misconfigured.
SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "CHANGE_ME_SET_JWT_SECRET_KEY_ENV_VAR"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hours

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
    The permission is read from Role.permissions, which is embedded in the JWT.

    Usage:
        @router.post("/execution/action")
        def execute(user=Depends(require_permission("can_execute_actions"))):
            ...
    """
    def _check(user: dict = Depends(get_current_user)):
        perms = user.get("permissions", {})
        if not (perms.get("is_admin") or perms.get(permission)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required.",
            )
        return user
    return _check
