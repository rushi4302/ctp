import base64
import hashlib
from datetime import datetime, timedelta, timezone
import secrets

import bcrypt
from jose import jwt

from fastapi.security import HTTPBearer

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

from secrets import token_urlsafe


# Password Hashing
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 600_000)
    return "pbkdf2_sha256${}${}${}".format(
        600_000,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            scheme, rounds, salt, expected = hashed_password.split("$", 3)
            salt_bytes = base64.urlsafe_b64decode(salt.encode("ascii"))
            expected_bytes = base64.urlsafe_b64decode(expected.encode("ascii"))
            actual = hashlib.pbkdf2_hmac(
                "sha256", plain_password.encode("utf-8"), salt_bytes, int(rounds)
            )
            return secrets.compare_digest(actual, expected_bytes)
        # Continue to accept existing bcrypt hashes. New hashes use PBKDF2 so
        # authentication does not depend on Passlib's incompatible bcrypt probe.
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("ascii"))
    except (ValueError, TypeError, UnicodeError):
        return False

from app.core.config import settings

# JWT Configuration sourced from application settings
def get_secret_key() -> str:
    return settings.jwt_secret_key

def get_algorithm() -> str:
    return settings.jwt_algorithm or "HS256"

def get_access_token_expire_minutes() -> int:
    return settings.access_token_expire_minutes or 60


def create_access_token(data: dict) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=get_access_token_expire_minutes()
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        get_secret_key(),
        algorithm=get_algorithm(),
    )


def decode_access_token(token: str):
    return jwt.decode(
        token,
        get_secret_key(),
        algorithms=[get_algorithm()],
    )


def generate_reset_token() -> str:
    return token_urlsafe(32)


def get_reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=30)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

