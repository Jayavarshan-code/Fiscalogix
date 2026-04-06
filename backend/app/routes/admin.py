from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
from app.Db.connections import get_db
from app.financial_system.auth import get_password_hash, require_permission
from setup_db import User, Profile, Role
import datetime

router = APIRouter(prefix="/admin", tags=["Admin User Management"])

# ─────────────────────────────────────────────────────────────────────────────
# MODEL HEALTH REGISTRY (Fix D — Heuristic Masking)
#
# WHAT WAS WRONG:
# When XGBoost/GNN failed to load, the system silently fell back to heuristics
# with confidence=0.70 but no external signal. A CFO could be making a $2M
# decision using a basic logistic equation while believing they have AI backing.
#
# HOW IT WAS FIXED:
# risk_engine.py now writes to this module-level registry on startup.
# The /admin/model-health endpoint exposes the registry for the Admin UI
# to surface a critical banner when any ML model is in fallback mode.
# ─────────────────────────────────────────────────────────────────────────────

MODEL_HEALTH_REGISTRY: Dict[str, dict] = {}

def register_model_status(model_name: str, status: str, detail: str = ""):
    """
    Called by ML model classes during __init__ to report their load status.
    status: 'ok' | 'fallback' | 'unavailable'
    """
    MODEL_HEALTH_REGISTRY[model_name] = {
        "status":     status,
        "detail":     detail,
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z"
    }

class UserCreate(BaseModel):
    username: str
    password: str
    profile_id: int
    role_id: int
    tenant_id: str = "default_tenant"

class UserResponse(BaseModel):
    id: int
    username: str
    profile_id: int
    role_id: int
    tenant_id: str

@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_permission("is_admin"))
):
    """Returns all registered users and their profiles. Requires is_admin."""
    users = db.query(User).all()
    profiles = db.query(Profile).all()
    roles = db.query(Role).all()
    profile_map = {p.id: p.name for p in profiles}
    role_map = {r.id: r.name for r in roles}

    return [
        {
            "id": u.id,
            "email": u.username,
            "profile_name": profile_map.get(u.profile_id, "Unknown"),
            "role_name": role_map.get(u.role_id, "Unknown"),
            "tenant_id": u.tenant_id,
        }
        for u in users
    ]

@router.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_permission("is_admin"))
):
    """Creates a new user with a role assignment. Requires is_admin."""
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    role = db.query(Role).filter(Role.id == user.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role {user.role_id} does not exist")

    new_user = User(
        tenant_id=user.tenant_id,
        username=user.username,
        hashed_password=get_password_hash(user.password),
        profile_id=user.profile_id,
        role_id=user.role_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "id": new_user.id,
        "username": new_user.username,
        "profile_id": new_user.profile_id,
        "role_id": new_user.role_id,
        "tenant_id": new_user.tenant_id,
    }

@router.get("/profiles")
def get_profiles(db: Session = Depends(get_db)):
    """Lookup available display profiles."""
    profiles = db.query(Profile).all()
    return [{"id": p.id, "name": p.name} for p in profiles]

@router.get("/roles")
def get_roles(
    db: Session = Depends(get_db),
    _current_user: dict = Depends(require_permission("is_admin"))
):
    """Lookup available roles and their permission sets. Requires is_admin."""
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "permissions": r.permissions} for r in roles]


@router.get("/model-health")
def get_model_health():
    """
    Returns the live load status of all ML models.
    Used by the Admin UI to surface a critical alert banner when any
    financial intelligence model is running in heuristic fallback mode.

    Response shape:
      overall_status: 'ok' | 'degraded' | 'critical'
      models: { model_name: { status, detail, updated_at } }
    """
    if not MODEL_HEALTH_REGISTRY:
        return {
            "overall_status": "unknown",
            "message": "No models have registered their status yet. Engine may be cold.",
            "models": {}
        }

    statuses = [m["status"] for m in MODEL_HEALTH_REGISTRY.values()]

    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "unavailable" for s in statuses):
        overall = "critical"
    else:
        overall = "degraded"

    return {
        "overall_status": overall,
        "models": MODEL_HEALTH_REGISTRY
    }
