from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.dependencies.auth import get_optional_current_user
from app.dependencies.database import get_db
from app.models import Report, User
from app.schemas.report import ReportResponse
from app.services.report_service import ReportService

router = APIRouter(prefix="/search")


@router.get("", response_model=List[ReportResponse], summary="Search public civic reports")
def search_reports(
    q: str = Query(..., min_length=2, max_length=200),
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_current_user),
):
    term = f"%{q.strip()}%"
    query = db.query(Report).filter(
        Report.moderation_status == "ACTIVE",
        or_(Report.title.ilike(term), Report.description.ilike(term), Report.category.ilike(term)),
    )
    if category:
        query = query.filter(Report.category == category.strip())
    if status_filter:
        query = query.filter(Report.status == status_filter.strip())
    report_ids = [
        row.id for row in query.order_by(Report.created_at.desc()).offset(skip).limit(limit)
    ]
    return [
        ReportService.get_report_by_id(db, report_id, current_user_id=user.id if user else None)
        for report_id in report_ids
    ]
