import pytest

from app.core.roles import UserRole
from app.core.security import verify_password
from scripts.create_admin import AdminBootstrapError, create_admin


def test_bootstrap_creates_hashed_admin_once(db):
    admin = create_admin(db, "  ADMIN@EXAMPLE.ORG ", "A-really-strong-demo-password")

    assert admin.email == "admin@example.org"
    assert admin.role == UserRole.ADMIN
    assert admin.is_active is True
    assert admin.hashed_password != "A-really-strong-demo-password"
    assert verify_password("A-really-strong-demo-password", admin.hashed_password)


def test_bootstrap_refuses_to_overwrite_existing_admin(db, admin_user):
    old_hash = admin_user.hashed_password

    with pytest.raises(AdminBootstrapError, match="administrator already exists"):
        create_admin(db, admin_user.email, "Another-strong-password")

    db.refresh(admin_user)
    assert admin_user.hashed_password == old_hash


def test_bootstrap_requires_strong_password_and_valid_email(db):
    with pytest.raises(AdminBootstrapError, match="valid email"):
        create_admin(db, "not-an-email", "A-really-strong-demo-password")
    with pytest.raises(AdminBootstrapError, match="12 to 128"):
        create_admin(db, "new-admin@example.org", "short")
