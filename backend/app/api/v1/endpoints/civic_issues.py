"""
Civic Issues Endpoint.

Manages municipal workflow on unique real-world civic issues.
Enforces backend Role-Based Access Control (RBAC) across Citizens,
Municipal Authorities, Administrators, and Field Workers.
"""

from datetime import datetime
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.services.storage_service import StorageService

from app.core.roles import UserRole
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models.user import User
from app.schemas.civic_issue import (
    CivicIssueAssignWorker,
    CivicIssueCategorySeverityUpdate,
    CivicIssueDetailResponse,
    CivicIssueResolution,
    CivicIssueResponse,
    CivicIssueStatusUpdate,
)
from app.services.civic_issue_service import CivicIssueService

router = APIRouter(prefix="/civic-issues", tags=["civic-issues"])
logger = logging.getLogger(__name__)


@router.get("", response_model=List[CivicIssueResponse], summary="List unique civic issues")
def get_civic_issues(
    skip: int = 0,
    limit: int = 50,
    status_filter: Optional[str] = None,
    category: Optional[str] = None,
    ward: Optional[str] = None,
    assigned_worker_id: Optional[int] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List unique real-world civic issues with optional filtering by status,
    category, ward, assigned worker, and proximity.
    """
    return CivicIssueService.get_civic_issues(
        db=db,
        status_filter=status_filter,
        category=category,
        ward=ward,
        assigned_worker_id=assigned_worker_id,
        skip=skip,
        limit=limit,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )


@router.get("/{issue_id}", response_model=CivicIssueDetailResponse, summary="Get civic issue detail")
def get_civic_issue_detail(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve full civic issue detail with all linked citizen reports and status logs.
    """
    issue = CivicIssueService.get_civic_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Civic Issue not found.",
        )
    return issue


@router.patch("/{issue_id}/status", response_model=CivicIssueResponse, summary="Update civic issue status")
def update_civic_issue_status(
    issue_id: int,
    status_in: CivicIssueStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates the status of a civic issue.
    Enforces RBAC:
      - Municipal Authorities & Admins: can update to any valid status.
      - Field Workers: can move assigned issues to IN_PROGRESS or RESOLVED.
      - Citizens: forbidden (HTTP 403).
    """
    return CivicIssueService.update_status(
        db=db,
        issue_id=issue_id,
        new_status=status_in.status.value,
        user=current_user,
        comment=status_in.comment,
    )


@router.patch("/{issue_id}/assign", response_model=CivicIssueResponse, summary="Assign field worker")
def assign_worker_to_issue(
    issue_id: int,
    assign_in: CivicIssueAssignWorker,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Assign a Field Worker to handle an issue.
    Accessible only to Municipal Authority and Admin.
    """
    return CivicIssueService.assign_worker(
        db=db,
        issue_id=issue_id,
        worker_id=assign_in.worker_id,
        department_id=assign_in.department_id,
        authority=authority,
        notes=assign_in.notes,
    )


@router.patch("/{issue_id}/category-severity", response_model=CivicIssueResponse, summary="Correct category or severity")
def correct_category_severity(
    issue_id: int,
    update_in: CivicIssueCategorySeverityUpdate,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Correct AI-predicted category or severity.
    Preserves original AI prediction for auditability.
    """
    return CivicIssueService.update_category_and_severity(
        db=db,
        issue_id=issue_id,
        authority=authority,
        category=update_in.category,
        severity=update_in.severity.value if update_in.severity else None,
        reason=update_in.reason,
    )


@router.post("/{issue_id}/resolve", response_model=CivicIssueResponse, summary="Resolve civic issue with evidence")
async def resolve_civic_issue(
    issue_id: int,
    resolution_notes: str = Form(..., min_length=5, max_length=2000),
    evidence_image: Optional[UploadFile] = File(None),
    resolution_latitude: Optional[float] = Form(None),
    resolution_longitude: Optional[float] = Form(None),
    resolution_timestamp: Optional[datetime] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([
        UserRole.ADMIN,
        UserRole.MUNICIPALITY,
        UserRole.FIELD_WORKER,
        UserRole.CONTRACTOR,
    ])),
):
    """
    Marks a civic issue as RESOLVED with resolution notes and optional proof media URL.
    Authorized for assigned Field Worker, Municipal Authority, or Admin.
    """
    uploaded_media_data = None
    try:
        if evidence_image:
            uploaded_media_data = await StorageService.save_upload(evidence_image)

        return CivicIssueService.resolve_with_evidence(
            db=db,
            issue_id=issue_id,
            user=current_user,
            resolution_notes=resolution_notes,
            resolution_evidence_url=(uploaded_media_data["file_url"] if uploaded_media_data else None),
            resolution_latitude=resolution_latitude,
            resolution_longitude=resolution_longitude,
            resolution_timestamp=resolution_timestamp,
        )
    except HTTPException:
        if uploaded_media_data:
            StorageService.delete_file(uploaded_media_data["file_name"])
        raise
    except Exception as exc:
        if uploaded_media_data:
            StorageService.delete_file(uploaded_media_data["file_name"])
        db.rollback()
        logger.exception("Resolution update failed for civic issue %s", issue_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Resolution update could not be saved. Please retry.",
        ) from exc


@router.post("/{issue_id}/reopen", response_model=CivicIssueResponse, summary="Request reopen (Still not resolved)")
def request_reopen(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Citizens can request to reopen an issue if it's marked resolved but still exists.
    """
    return CivicIssueService.request_reopen(
        db=db,
        issue_id=issue_id,
        user=current_user,
    )
