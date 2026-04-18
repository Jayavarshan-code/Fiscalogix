import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.Db.connections import SessionLocal
from setup_db import User, Role, Profile
from app.financial_system.auth import get_password_hash

def main():
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter_by(name="system_admin").first()
        admin_profile = db.query(Profile).filter_by(name="System Admin").first()
        
        email = "superadmin@fiscalogix.com"
        password = "SuperAdmin123!"

        # Create user
        new_user = User(
            tenant_id="default_tenant",
            username=email,
            hashed_password=get_password_hash(password),
            role_id=admin_role.id,
            profile_id=admin_profile.id,
        )
        db.add(new_user)
        db.commit()
        print(f"Account Created!")
        print(f"Email: {email}")
        print(f"Password: {password}")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
