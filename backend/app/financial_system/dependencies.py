from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.financial_system.auth import decode_access_token
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    JWT dependency for protected routes.
    Decodes the Bearer token and returns the payload (user_id, tenant_id, profile_name).
    Raises 401 if the token is invalid or expired.
    """
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
