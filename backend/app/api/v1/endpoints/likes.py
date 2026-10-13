from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.models.user import User
from app.services.report_service import ReportService

router = APIRouter(prefix="/likes", tags=["likes"])


@router.post("/{report_id}", summary="Toggle the current user's report upvote")
def toggle_like(
    report_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ReportService.toggle_upvote(db=db, report_id=report_id, user=user)
