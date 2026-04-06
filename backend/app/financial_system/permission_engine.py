from sqlalchemy.orm import Session
from setup_db import User, Role


class PermissionEngine:
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> dict:
        """
        Role-based permission resolution.
        Permissions are stored as a JSON dict on Role.permissions.
        This is the single source of truth — no PermissionSet layering needed.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        role = db.query(Role).filter(Role.id == user.role_id).first()
        return role.permissions.copy() if role and role.permissions else {}

    @staticmethod
    def check_permission(db: Session, user_id: int, permission_name: str) -> bool:
        perms = PermissionEngine.get_user_permissions(db, user_id)
        return bool(perms.get("is_admin") or perms.get(permission_name, False))
