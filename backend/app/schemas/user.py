from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.roles import UserRole

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Optional[UserRole] = UserRole.CITIZEN

    @field_validator("role")
    @classmethod
    def public_registration_is_citizen_only(cls, value):
        if value != UserRole.CITIZEN:
            raise ValueError("Public registration only supports citizen accounts.")
        return value


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool

    model_config = {
        "from_attributes": True
    }


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None

    @field_validator("full_name")
    @classmethod
    def trim_name(cls, value):
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank.")
        return value


class UserSummaryResponse(BaseModel):
    id: int
    full_name: str

    model_config = {"from_attributes": True}


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
    new_password: str = Field(min_length=8, max_length=128)
