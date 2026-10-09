from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies.database import get_db
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService
from app.schemas.user import UserLogin, Token

from app.dependencies.auth import get_current_user
from app.models.user import User

from app.dependencies.roles import require_role
from app.core.roles import UserRole

from app.schemas.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
)


router = APIRouter()


@router.post("/register", response_model=UserResponse)
def register(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return UserService.create_user(db, user)

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    

@router.post("/login", response_model=Token)
def login(
    user: UserLogin,
    db: Session = Depends(get_db),
):
    try:
        return UserService.login_user(db, user)

    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=str(e),
        )



@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/admin-test")
def admin_test(
    current_user=Depends(require_role(UserRole.ADMIN)),
):
    return {
        "message": "Welcome Admin",
        "user": current_user.full_name,
    }


@router.get("/citizen-test")
def citizen_test(
    current_user=Depends(require_role(UserRole.CITIZEN)),
):
    return {
        "message": "Welcome Citizen",
        "user": current_user.full_name,
    }




@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return UserService.forgot_password(
        request.email,
        db,
        background_tasks,
    )


@router.post("/reset-password")
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        return UserService.reset_password(
            request.token,
            request.new_password,
            db,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    



    