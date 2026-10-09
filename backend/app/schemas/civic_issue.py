"""
Schemas for Civic Issues, Field Worker assignments, Admin moderation,
Transparency Statistics, and Civic Health Scores.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.constants import CivicIssueStatus, ReportSeverity
from app.schemas.user import UserResponse


class CivicIssueStatusLogResponse(BaseModel):
    id: int
    civic_issue_id: int
    changed_by_id: Optional[int] = None
    previous_status: str
    new_status: str
    comment: Optional[str] = None
    created_at: datetime
    changed_by: Optional[UserResponse] = None

    model_config = {"from_attributes": True}


class CivicIssueResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    status: str
    severity: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    ward: Optional[str] = None
    report_count: int = 1
    assigned_department_id: Optional[str] = None
    assigned_worker_id: Optional[int] = None
    assigned_worker: Optional[UserResponse] = None
    ai_category: Optional[str] = None
    ai_confidence: Optional[float] = None
    resolution_notes: Optional[str] = None
    resolution_evidence_url: Optional[str] = None
    resolution_latitude: Optional[float] = None
    resolution_longitude: Optional[float] = None
    resolution_timestamp: Optional[datetime] = None
    resolution_location_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


from app.schemas.report import ReportResponse


class CivicIssueDetailResponse(CivicIssueResponse):
    reports: List[ReportResponse] = []
    status_logs: List[CivicIssueStatusLogResponse] = []

    model_config = {"from_attributes": True}



class CivicIssueStatusUpdate(BaseModel):
    status: CivicIssueStatus
    comment: Optional[str] = Field(None, max_length=500)


class CivicIssueAssignWorker(BaseModel):
    worker_id: int
    department_id: Optional[str] = None
    notes: Optional[str] = Field(None, max_length=500)


class CivicIssueCategorySeverityUpdate(BaseModel):
    category: Optional[str] = None
    severity: Optional[ReportSeverity] = None
    reason: Optional[str] = Field(None, max_length=500)


class CivicIssueResolution(BaseModel):
    resolution_notes: str = Field(..., min_length=5, max_length=2000)
    resolution_evidence_url: Optional[str] = None


class ReportModerationRequest(BaseModel):
    action: str = Field(..., description="Action: 'REJECT' or 'RESTORE'")
    reason: Optional[str] = Field(None, max_length=500)


class HealthScoreComponent(BaseModel):
    score: float
    weight: float
    description: str


class CivicHealthScoreResponse(BaseModel):
    overall_score: float
    rating: str
    ward: Optional[str] = None
    total_issues_analyzed: int
    components: Dict[str, HealthScoreComponent]


class TransparencyStatsResponse(BaseModel):
    total_valid_reports: int
    total_unique_civic_issues: int
    pending_issues: int
    assigned_issues: int
    in_progress_issues: int
    resolved_issues: int
    closed_issues: int
    open_issues: int
    high_critical_issues: int
    average_resolution_hours: Optional[float] = None
    category_distribution: Dict[str, int]
    ward_distribution: Dict[str, int]
    multi_report_issues_count: int


class PublicIssueMapPoint(BaseModel):
    id: int
    category: str
    severity: str
    status: str
    latitude: float
    longitude: float
    locality: Optional[str] = None
    ward: Optional[str] = None
    report_count: int
