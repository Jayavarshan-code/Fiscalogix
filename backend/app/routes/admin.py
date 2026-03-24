from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.Db.connections import get_db
from app.financial_system.auth import get_password_hash
from setup_db import User, Profile

router = APIRouter(prefix="/admin", tags=["Admin User Management"])

class UserCreate(BaseModel):
    username: str
    password: str
    profile_id: int
    tenant_id: str = "default_tenant"

class UserResponse(BaseModel):
    id: int
    username: str
    profile_id: int
    tenant_id: str

@router.get("/users")
def get_all_users(db: Session = Depends(get_db)):
    """
    Returns all registered users and their profiles.
    (In production, this should be gated by an `is_admin` dependency).
    """
    users = db.query(User).all()
    profiles = db.query(Profile).all()
    profile_map = {p.id: p.name for p in profiles}
    
    return [
        {
            "id": u.id,
            "email": u.username,
            "profile_name": profile_map.get(u.profile_id, "Unknown"),
            "tenant_id": u.tenant_id
        }
        for u in users
    ]

@router.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user. Assigns them a profile.
    """
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    new_user = User(
        tenant_id=user.tenant_id,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        profile_id=user.profile_id
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "username": new_user.username,
        "profile_id": new_user.profile_id,
        "tenant_id": new_user.tenant_id
    }

@router.get("/profiles")
def get_profiles(db: Session = Depends(get_db)):
    """
    Lookup available RBAC Profiles.
    """
    profiles = db.query(Profile).all()
    return [{"id": p.id, "name": p.name, "permissions": p.permissions} for p in profiles]
