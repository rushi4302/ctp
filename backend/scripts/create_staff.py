"""Create an authorized municipal or field-worker account in civic_db_test."""

from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url

from app.core.roles import UserRole
from app.core.security import hash_password
from app.core.config import settings
from app.database.session import SessionLocal
from app.models.user import User
from scripts.create_admin import AdminBootstrapError


def main() -> int:
    url = make_url(settings.database_url)
    if url.database != "civic_db_test" or url.username != "civic_user":
        raise SystemExit("Refusing staff creation: configured database is not civic_db_test.")

    db = SessionLocal()
    try:
        if db.execute(text("SELECT current_database()")).scalar_one() != "civic_db_test":
            raise SystemExit("Refusing staff creation: server connection is not civic_db_test.")
        if not db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)):
            raise AdminBootstrapError("Create the initial administrator first.")

        full_name = input("Staff full name: ").strip()
        email = input("Staff email: ").strip().lower()
        role_name = input("Staff role (municipality/field_worker): ").strip().lower()
        if role_name not in {UserRole.MUNICIPALITY.value, UserRole.FIELD_WORKER.value}:
            raise AdminBootstrapError("Role must be municipality or field_worker.")
        password = getpass.getpass("Temporary password (12+ characters): ")
        if (
            len(full_name) < 2
            or len(full_name) > 100
            or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
            or len(password) < 12
            or len(password) > 128
        ):
            raise AdminBootstrapError("Enter a valid email, a 2–100 character name, and a 12–128 character password.")
        if db.scalar(select(User.id).where(User.email == email)):
            raise AdminBootstrapError("That email is already registered. No account was changed.")

        user = User(
            full_name=full_name,
            email=email,
            hashed_password=hash_password(password),
            role=UserRole(role_name),
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created {role_name} account {email} (user id {user.id}) in civic_db_test.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AdminBootstrapError as error:
        raise SystemExit(str(error))
