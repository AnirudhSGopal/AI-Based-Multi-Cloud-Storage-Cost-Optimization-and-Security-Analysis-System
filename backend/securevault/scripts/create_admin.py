"""
Seed script — create the admin user in the database.

Usage:
    cd backend/securevault
    python scripts/create_admin.py

Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment / .env.
If the user already exists, updates the role to ADMIN.
"""
import os
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.core.factory import create_app
from app.core.extensions import db
from app.models.user import User, RoleEnum


def seed_admin():
    app = create_app("development")
    with app.app_context():
        email = os.getenv("ADMIN_EMAIL", "admin@cloudopt.ai").strip().lower()
        password = os.getenv("ADMIN_PASSWORD")
        if not password or not password.strip():
            raise RuntimeError("ADMIN_PASSWORD environment variable is required to bootstrap or update the admin user.")
        username = os.getenv("ADMIN_USERNAME", "admin")

        user = User.query.filter_by(email=email).first()

        if user:
            user.role = RoleEnum.ADMIN
            user.password = password
            db.session.commit()
            print(f"[OK] Updated user '{email}' to ADMIN role and reset password from ADMIN_PASSWORD.")
        else:
            user = User(
                username=username,
                email=email,
                role=RoleEnum.ADMIN,
                is_active=True,
            )
            user.password = password
            db.session.add(user)
            db.session.commit()
            print(f"[OK] Created admin user: {email} (id={user.id})")

        print(f"    email    = {email}")
        print(f"    username = {user.username}")
        print(f"    role     = {user.role.value}")


if __name__ == "__main__":
    seed_admin()
