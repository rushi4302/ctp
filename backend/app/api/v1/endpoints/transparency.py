"""
Transparency Endpoints.

Provides public-safe statistics, explainable Civic Health Scores,
and map visualization data.
Enforces data safety: rejected or hidden spam submissions do not inflate
public statistics, and private personal data is never exposed.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.constants import CivicIssueStatus
from app.dependencies.database import get_db
from app.models.report import CivicIssue
from app.schemas.civic_issue import (
    CivicHealthScoreResponse,
    PublicIssueMapPoint,
    TransparencyStatsResponse,
)
from app.services.civic_issue_service import CivicIssueService

router = APIRouter(prefix="/transparency", tags=["transparency"])


@router.get("/stats", response_model=TransparencyStatsResponse, summary="Public civic transparency statistics")
def get_transparency_statistics(
    ward: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns public civic statistics:
    - Total valid citizen submissions vs unique real-world civic issues
    - Status breakdown (pending, assigned, in progress, resolved, closed)
    - Average resolution time
    - Category distribution
    - Ward-level breakdown
    """
    return CivicIssueService.get_transparency_statistics(db=db, ward=ward)


@router.get("/health-score", response_model=CivicHealthScoreResponse, summary="Explainable Civic Health Score")
def get_civic_health_score(
    ward: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Calculates the explainable Civic Health Score (0 - 100) using:
      - Resolution Score (30%)
      - Response / Handling Rate (20%)
      - Severity Health (25%)
      - Pending Age Health (15%)
      - Recurrence Health (10%)
    Provides transparent mathematical justification and breakdown.
    """
    return CivicIssueService.calculate_civic_health_score(db=db, ward=ward)


@router.get("/map", response_model=List[PublicIssueMapPoint], summary="Public issue map data")
def get_public_issue_map(
    ward: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns sanitized geographic points for civic issues map view.
    Excludes sensitive citizen identity information.
    """
    query = db.query(CivicIssue).filter(
        CivicIssue.status.in_([
            CivicIssueStatus.PENDING.value,
            CivicIssueStatus.ASSIGNED.value,
            CivicIssueStatus.IN_PROGRESS.value,
            CivicIssueStatus.RESOLVED.value,
        ])
    )

    if ward and ward.strip():
        query = query.filter(CivicIssue.ward == ward.strip())
    if category and category.strip():
        query = query.filter(CivicIssue.category == category.strip())

    issues = query.all()

    return [
        PublicIssueMapPoint(
            id=issue.id,
            category=issue.category,
            severity=issue.severity,
            status=issue.status,
            latitude=issue.latitude,
            longitude=issue.longitude,
            locality=issue.locality,
            ward=issue.ward,
            report_count=issue.report_count,
        )
        for issue in issues
    ]
