from typing import Optional
from pydantic import BaseModel, EmailStr
from app.core.roles import UserRole

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: Optional[UserRole] = UserRole.CITIZEN


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = {
        "from_attributes": True
    }


from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):

    token: str
    new_password: str