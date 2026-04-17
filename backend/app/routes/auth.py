from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.Db.connections import get_db
from app.financial_system.auth import (
    verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.rate_limiter import limiter
from setup_db import User, Profile

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login")
@limiter.limit("10/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get Profile Name for the token payload (Frontend convenience)
    profile = db.query(Profile).filter(Profile.id == user.profile_id).first()
    profile_name = profile.name if profile else "Standard User"

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Load Role permissions so every protected route can gate without a DB call
    from setup_db import Role
    role = db.query(Role).filter(Role.id == user.role_id).first()
    role_permissions = role.permissions if role else {}

    payload = {
        "sub": user.username,
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "profile_name": profile_name,
        "permissions": role_permissions,   # embedded so require_permission() is DB-free
    }
    
    access_token = create_access_token(
        data=payload, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "profile_name": profile_name,
        "email": user.username,
        "permissions": role_permissions,   # forwarded so frontend can gate UI without JWT decode
    }
