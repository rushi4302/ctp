from passlib.context import CryptContext
import hashlib
from datetime import datetime, timedelta, timezone
from jose import jwt

from fastapi.security import HTTPBearer

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

from secrets import token_urlsafe
from datetime import datetime, timedelta


# Password Hashing
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password,
    )

from app.core.config import settings

# JWT Configuration sourced from application settings
def get_secret_key() -> str:
    return settings.jwt_secret_key or "civic-intelligence-secret-key-32-chars-long-4302"

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



