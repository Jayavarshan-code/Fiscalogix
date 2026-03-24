from sqlalchemy.orm import Session
from setup_db import User, Profile, PermissionSet, UserPermissionSet

class PermissionEngine:
    @staticmethod
    def get_user_permissions(db: Session, user_id: int) -> dict:
        """
        Salesforce-style permission resolution:
        Permissions = Profile Permissions + Union of all Permission Set Permissions
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # 1. Get Base Profile Permissions
        profile = db.query(Profile).filter(Profile.id == user.profile_id).first()
        effective_permissions = profile.permissions.copy() if profile and profile.permissions else {}

        # 2. Layer on Permission Sets
        perm_set_ids = db.query(UserPermissionSet.permission_set_id).filter(UserPermissionSet.user_id == user_id).all()
        perm_set_ids = [pid[0] for pid in perm_set_ids]
        
        if perm_set_ids:
            perm_sets = db.query(PermissionSet).filter(PermissionSet.id.in_(perm_set_ids)).all()
            for ps in perm_sets:
                if ps.permissions:
                    for key, val in ps.permissions.items():
                        # Permissions are additive (True wins)
                        if val is True:
                            effective_permissions[key] = True
        
        return effective_permissions

    @staticmethod
    def check_permission(db: Session, user_id: int, permission_name: str) -> bool:
        perms = PermissionEngine.get_user_permissions(db, user_id)
        return perms.get(permission_name, False)
