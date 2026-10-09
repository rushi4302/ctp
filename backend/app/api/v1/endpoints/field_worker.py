"""
Field Worker Endpoints.

Dedicated workflow for on-ground municipal field workers and contractors:
- View assigned civic issues
- Update work progress to IN_PROGRESS
- Submit resolution evidence and notes
Enforces RBAC so field workers can only interact with tasks assigned to them.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.constants import CivicIssueStatus
from app.core.roles import UserRole
from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models.user import User
from app.schemas.civic_issue import (
    CivicIssueDetailResponse,
    CivicIssueResolution,
    CivicIssueResponse,
)
from app.services.civic_issue_service import CivicIssueService

router = APIRouter(prefix="/field-worker", tags=["field-worker"])


@router.get("/issues", response_model=List[CivicIssueResponse], summary="List assigned issues for field worker")
def get_assigned_issues(
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    worker: User = Depends(require_roles([UserRole.FIELD_WORKER, UserRole.CONTRACTOR])),
):
    """
    Returns civic issues specifically assigned to the authenticated field worker.
    """
    return CivicIssueService.get_civic_issues(
        db=db,
        status_filter=status_filter,
        assigned_worker_id=worker.id,
        skip=skip,
        limit=limit,
    )


@router.get("/issues/{issue_id}", response_model=CivicIssueDetailResponse, summary="Get assigned issue detail")
def get_assigned_issue_detail(
    issue_id: int,
    db: Session = Depends(get_db),
    worker: User = Depends(require_roles([UserRole.FIELD_WORKER, UserRole.CONTRACTOR])),
):
    """
    Returns full detail of an assigned issue for field execution.
    """
    issue = CivicIssueService.get_civic_issue_by_id(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Civic Issue not found.")
    if issue.assigned_worker_id != worker.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this civic issue.",
        )
    return issue


@router.post("/issues/{issue_id}/progress", response_model=CivicIssueResponse, summary="Mark issue in progress")
def mark_issue_in_progress(
    issue_id: int,
    progress_notes: str = "Field inspection and work commenced.",
    db: Session = Depends(get_db),
    worker: User = Depends(require_roles([UserRole.FIELD_WORKER, UserRole.CONTRACTOR])),
):
    """
    Moves issue from ASSIGNED to IN_PROGRESS.
    """
    return CivicIssueService.update_status(
        db=db,
        issue_id=issue_id,
        new_status=CivicIssueStatus.IN_PROGRESS.value,
        user=worker,
        comment=progress_notes,
    )


@router.post("/issues/{issue_id}/resolve", response_model=CivicIssueResponse, summary="Submit resolution evidence")
def submit_issue_resolution(
    issue_id: int,
    resolution_in: CivicIssueResolution,
    db: Session = Depends(get_db),
    worker: User = Depends(require_roles([UserRole.FIELD_WORKER, UserRole.CONTRACTOR])),
):
    """
    Resolves the assigned issue with work notes and optional evidence media.
    """
    return CivicIssueService.resolve_with_evidence(
        db=db,
        issue_id=issue_id,
        user=worker,
        resolution_notes=resolution_in.resolution_notes,
        resolution_evidence_url=resolution_in.resolution_evidence_url,
    )
