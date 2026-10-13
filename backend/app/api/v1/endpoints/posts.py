from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import get_optional_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=List[ReportResponse], summary="List public civic report posts")
def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    return ReportService.get_reports(
        db=db,
        current_user_id=user.id if user else None,
        skip=skip,
        limit=limit,
        category=category,
        status_filter=status_filter,
    )
