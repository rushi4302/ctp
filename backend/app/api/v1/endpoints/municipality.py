from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models.user import User
from app.schemas.report import ReportDetailResponse, ReportResponse, StatusUpdateSchema
from app.services.report_service import ReportService

router = APIRouter(prefix="/municipality")


@router.get("", summary="Check municipality module status")
def municipality_status() -> dict[str, str]:
    return {"module": "municipality", "status": "ready"}


@router.get("/stats", summary="Get municipal dashboard statistics")
def get_municipality_stats(
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Returns counts by report status and category for administrative dashboards.
    """
    return ReportService.get_statistics(db)


@router.get("/reports", response_model=List[ReportResponse], summary="List reports for municipal staff")
def get_municipality_reports(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Lists reports across the jurisdiction with optional status and category filters.
    """
    return ReportService.get_reports(
        db=db,
        current_user_id=authority.id,
        category=category,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/reports/{report_id}", response_model=ReportDetailResponse, summary="Get full report detail for municipal staff")
def get_municipality_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    report_dict = ReportService.get_report_by_id(db, report_id, current_user_id=authority.id)
    if not report_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return report_dict


@router.patch("/reports/{report_id}/status", response_model=ReportResponse, summary="Update report status")
def update_report_status(
    report_id: int,
    status_in: StatusUpdateSchema,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Verify, resolve, reject, or assign a report.
    """
    return ReportService.update_status(
        db=db,
        report_id=report_id,
        authority=authority,
        status_in=status_in,
    )


@router.get("/civic-issues", response_model=List[dict], summary="List civic issues for municipal authority")
def get_municipality_civic_issues(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    ward: Optional[str] = None,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    from app.services.civic_issue_service import CivicIssueService
    issues = CivicIssueService.get_civic_issues(
        db=db,
        status_filter=status_filter,
        category=category,
        ward=ward,
        skip=skip,
        limit=limit,
    )
    return [
        {
            "id": i.id,
            "title": i.title,
            "description": i.description,
            "category": i.category,
            "status": i.status,
            "severity": i.severity,
            "latitude": i.latitude,
            "longitude": i.longitude,
            "locality": i.locality,
            "ward": i.ward,
            "report_count": i.report_count,
            "assigned_worker_id": i.assigned_worker_id,
            "ai_category": i.ai_category,
            "ai_confidence": i.ai_confidence,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
            "resolved_at": i.resolved_at,
        }
        for i in issues
    ]


@router.get("/ward-stats", summary="Get ward level civic statistics")
def get_municipality_ward_stats(
    ward: Optional[str] = None,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    from app.services.civic_issue_service import CivicIssueService
    return CivicIssueService.get_transparency_statistics(db=db, ward=ward)

