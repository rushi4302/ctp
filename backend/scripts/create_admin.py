"""Secure one-time bootstrap for an administrator in civic_db_test.

Run from ``backend`` with ``../ctp_env/bin/python scripts/create_admin.py``.
The password is entered through getpass and is never written to output/logs.
"""

from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.user import User


class AdminBootstrapError(RuntimeError):
    """A safe refusal to create or overwrite an administrator."""


def create_admin(db: Session, email: str, password: str) -> User:
    """Create the initial administrator; never alter an existing account."""
    normalized_email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized_email):
        raise AdminBootstrapError("Enter a valid email address.")
    if len(password) < 12 or len(password) > 128:
        raise AdminBootstrapError("Admin password must contain 12 to 128 characters.")

    if db.scalar(select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)):
        raise AdminBootstrapError(
            "An administrator already exists. No account was changed."
        )
    if db.scalar(select(User.id).where(User.email == normalized_email)):
        raise AdminBootstrapError(
            "That email is already registered. No account was changed."
        )

    user = User(
        full_name="Administrator",
        email=normalized_email,
        hashed_password=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def main() -> int:
    url = make_url(settings.database_url)
    if url.database != "civic_db_test" or url.username != "civic_user":
        raise SystemExit("Refusing admin bootstrap: configured database is not civic_db_test.")

    db = SessionLocal()
    try:
        actual_database = db.execute(text("SELECT current_database()")).scalar_one()
        if actual_database != "civic_db_test":
            raise SystemExit(
                "Refusing admin bootstrap: server connection is not civic_db_test."
            )

        email = input("Administrator email: ").strip()
        password = getpass.getpass("Administrator password (12+ characters): ")
        confirmation = getpass.getpass("Confirm administrator password: ")
        if password != confirmation:
            raise AdminBootstrapError("Passwords do not match. No account was created.")

        admin = create_admin(db, email, password)
        db.commit()
        print(f"Created administrator {admin.email} (user id {admin.id}) in civic_db_test.")
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
