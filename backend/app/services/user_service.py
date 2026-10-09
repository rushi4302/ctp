from datetime import datetime, timezone
import asyncio
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin
from app.core.roles import UserRole
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    generate_reset_token,
    get_reset_token_expiry,
    hash_reset_token,
)
from app.utils.email import send_reset_email


class UserService:

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:

        existing_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if existing_user:
            raise ValueError("Email already registered")

        now = datetime.now(timezone.utc)
        db_user = User(
            full_name=user.full_name,
            email=user.email,
            hashed_password=hash_password(user.password),
            role=user.role if user.role else UserRole.CITIZEN,
            created_at=now,
            updated_at=now,
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return db_user

    @staticmethod
    def login_user(db: Session, user: UserLogin):

        db_user = (
            db.query(User)
            .filter(User.email == user.email)
            .first()
        )

        if not db_user:
            raise ValueError("Invalid email or password")

        if not verify_password(
            user.password,
            db_user.hashed_password,
        ):
            raise ValueError("Invalid email or password")

        token = create_access_token(
            {
                "sub": str(db_user.id),
                "email": db_user.email,
                "role": db_user.role.value,
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
        }

    @staticmethod
    def forgot_password(email: str, db: Session, background_tasks: BackgroundTasks | None = None):

        user = (
            db.query(User)
            .filter(User.email == email)
            .first()
        )

        # Don't reveal whether the email exists
        if user is None:
            return {
                "message": "If an account exists, a password reset email has been sent."
            }

        token = generate_reset_token()

        # Store only the hash
        user.reset_token = hash_reset_token(token)
        user.reset_token_expiry = get_reset_token_expiry()

        db.commit()

        # Dispatch reset email non-blockingly via background task
        if background_tasks is not None:
            background_tasks.add_task(send_reset_email, user.email, token)
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(send_reset_email(user.email, token))
                else:
                    loop.run_until_complete(send_reset_email(user.email, token))
            except Exception:
                pass

        return {
            "message": "If an account exists, a password reset email has been sent."
        }

    @staticmethod
    def reset_password(token: str, new_password: str, db: Session):

        hashed_token = hash_reset_token(token)

        user = (
            db.query(User)
            .filter(User.reset_token == hashed_token)
            .first()
        )

        if user is None:
            raise ValueError("Invalid reset token.")

        now = datetime.now(timezone.utc)
        expiry = user.reset_token_expiry
        if expiry is not None and expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)

        if expiry is None or expiry < now:
            raise ValueError("Reset token has expired.")

        user.hashed_password = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        user.updated_at = now

        db.commit()

        return {
            "message": "Password reset successfully."
        }