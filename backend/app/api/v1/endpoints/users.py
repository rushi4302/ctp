from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.user import UserProfileUpdate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
def get_my_profile(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserResponse, summary="Update current user profile")
def update_my_profile(
    changes: UserProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    fields = changes.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Provide a name or email to update.")
    if "email" in fields:
        fields["email"] = str(fields["email"]).lower()
        existing = db.scalar(select(User.id).where(User.email == fields["email"], User.id != user.id))
        if existing:
            raise HTTPException(status_code=409, detail="That email is already in use.")
    for field, value in fields.items():
        setattr(user, field, value)
    try:
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Profile could not be updated.",
        )
    return user
