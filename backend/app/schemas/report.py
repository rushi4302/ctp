from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from app.core.constants import LocationValidationStatus, ReportSeverity, ReportStatus
from app.schemas.user import UserResponse


class MediaResponse(BaseModel):
    id: int
    report_id: int
    file_url: str
    file_name: str
    file_type: str
    file_size: int
    exif_latitude: Optional[float] = None
    exif_longitude: Optional[float] = None
    exif_timestamp: Optional[datetime] = None
    capture_timestamp: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=1000)


class CommentResponse(BaseModel):
    id: int
    report_id: int
    user_id: int
    content: str
    created_at: datetime
    user: Optional[UserResponse] = None

    model_config = {"from_attributes": True}


class StatusLogResponse(BaseModel):
    id: int
    report_id: int
    changed_by_id: Optional[int] = None
    previous_status: str
    new_status: str
    comment: Optional[str] = None
    created_at: datetime
    changed_by: Optional[UserResponse] = None

    model_config = {"from_attributes": True}


class ReportCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    description: str = Field(..., min_length=5, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)
    severity: Optional[ReportSeverity] = ReportSeverity.MEDIUM
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_accuracy: Optional[float] = None
    capture_timestamp: Optional[datetime] = None
    address: Optional[str] = Field(None, max_length=255)
    locality: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    district: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    ward: Optional[str] = Field(None, max_length=100)


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=150)
    description: Optional[str] = Field(None, min_length=5, max_length=2000)
    category: Optional[str] = Field(None, max_length=100)
    severity: Optional[ReportSeverity] = None
    address: Optional[str] = None
    ward: Optional[str] = None


class StatusUpdateSchema(BaseModel):
    status: ReportStatus
    comment: Optional[str] = Field(None, max_length=500)
    assigned_department_id: Optional[str] = None
    contractor_id: Optional[int] = None


class ReportResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    status: str
    severity: str
    latitude: float
    longitude: float
    location_accuracy: Optional[float] = None
    capture_timestamp: Optional[datetime] = None
    address: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    ward: Optional[str] = None
    reporter_id: int
    assigned_department_id: Optional[str] = None
    contractor_id: Optional[int] = None
    ai_category: Optional[str] = None
    ai_confidence: Optional[float] = None
    location_validation_status: str
    created_at: datetime
    updated_at: datetime
    upvotes_count: int = 0
    has_upvoted: bool = False
    civic_issue_id: Optional[int] = None
    moderation_status: str = "ACTIVE"
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    media: List[MediaResponse] = []

    model_config = {"from_attributes": True}



class ReportDetailResponse(ReportResponse):
    reporter: Optional[UserResponse] = None
    contractor: Optional[UserResponse] = None
    comments: List[CommentResponse] = []
    status_logs: List[StatusLogResponse] = []

    model_config = {"from_attributes": True}


class AIAnalysisResponse(BaseModel):
    suggested_category: Optional[str] = None
    suggested_confidence: Optional[float] = None
    primary_source: str
    text_analysis: Optional[dict] = None
    image_analysis: Optional[dict] = None
