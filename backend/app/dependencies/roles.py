from typing import Sequence
from fastapi import Depends, HTTPException, status

from app.dependencies.auth import get_current_user
from app.core.roles import UserRole


def require_role(required_role: UserRole):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource.",
            )
        return current_user

    return role_checker


def require_roles(allowed_roles: Sequence[UserRole]):
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource.",
            )
        return current_user

    return role_checker