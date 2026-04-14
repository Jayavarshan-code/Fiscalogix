"""
Tenant Self-Registration — POST /auth/register

Creates a new tenant + admin user + default financial parameters in one call.
No manual seed_db.py run required.

Security:
  - Duplicate username → 409
  - Password hashed with bcrypt before storage
  - Returns a JWT immediately so the client can proceed without a second login
"""

import uuid
import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    company_name: str
    email: str
    password: str
    industry_vertical: str = "logistics"

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v

    @field_validator("email")
    @classmethod
    def email_format(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address.")
        return v.lower().strip()


@router.post("/register", status_code=201)
def register_tenant(payload: RegisterRequest):
    """
    Self-service tenant onboarding.

    1. Generates a unique tenant_id slug from the company name.
    2. Creates a User row with bcrypt-hashed password.
    3. Seeds financial_parameters with sensible defaults for the chosen vertical.
    4. Returns an access token — client is logged in immediately.
    """
    from app.Db.connections import SessionLocal
    from app.financial_system.auth import verify_password, create_access_token
    from app.financial_system.wacc_engine import _DAMODARAN_WACC

    # Slugify company name → tenant_id
    slug = payload.company_name.lower().replace(" ", "_").replace("-", "_")
    slug = "".join(c for c in slug if c.isalnum() or c == "_")
    tenant_id = f"{slug}_{uuid.uuid4().hex[:6]}"

    db = SessionLocal()
    try:
        # Import models — deferred to avoid circular imports at module level
        from setup_db import User, Role, Profile, FinancialParameters

        # Check for duplicate email
        existing = db.query(User).filter(User.username == payload.email).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        # Hash password
        from passlib.context import CryptContext
        pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_ctx.hash(payload.password)

        # Get or create default role (Admin)
        role = db.query(Role).filter(Role.name == "Admin").first()
        if not role:
            role = Role(
                name="Admin",
                permissions={
                    "view_dashboard": True,
                    "manage_users": True,
                    "export_reports": True,
                    "configure_alerts": True,
                },
            )
            db.add(role)
            db.flush()

        # Create profile
        profile = Profile(name="Administrator")
        db.add(profile)
        db.flush()

        # Create user
        user = User(
            username=payload.email,
            hashed_password=hashed,
            tenant_id=tenant_id,
            role_id=role.id,
            profile_id=profile.id,
        )
        db.add(user)
        db.flush()

        # Seed financial parameters with vertical-aware WACC default
        wacc_default = _DAMODARAN_WACC.get(payload.industry_vertical, _DAMODARAN_WACC["default"])
        fp = FinancialParameters(
            tenant_id=tenant_id,
            wacc=wacc_default,
            penalty_rate=0.02,   # 2% per day SLA breach — typical MSA default
        )
        db.add(fp)
        db.commit()
        db.refresh(user)

        logger.info(f"[register] New tenant created: tenant_id={tenant_id} email={payload.email}")

        # Issue JWT immediately — user is logged in
        token = create_access_token(data={
            "sub":          payload.email,
            "user_id":      user.id,
            "tenant_id":    tenant_id,
            "profile_name": "Administrator",
            "permissions":  role.permissions,
        })

        return {
            "access_token":  token,
            "token_type":    "bearer",
            "user_id":       user.id,
            "tenant_id":     tenant_id,
            "profile_name":  "Administrator",
            "email":         payload.email,
            "permissions":   role.permissions,
            "message":       f"Tenant '{payload.company_name}' created. You are now logged in.",
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[register] Tenant creation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        db.close()
