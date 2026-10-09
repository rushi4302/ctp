from datetime import datetime
from typing import Any, List, Optional
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.constants import ReportSeverity, ReportStatus
from app.core.roles import UserRole
from app.dependencies.auth import get_current_user, get_optional_current_user
from app.dependencies.database import get_db
from app.dependencies.roles import require_roles
from app.models.user import User
from app.schemas.report import (
    AIAnalysisResponse,
    CommentCreate,
    CommentResponse,
    ReportCreate,
    ReportDetailResponse,
    ReportResponse,
    ReportUpdate,
    StatusUpdateSchema,
)
from app.schemas.civic_issue import ReportModerationRequest
from app.services.ai_service import AIService
from app.services.civic_issue_service import CivicIssueService
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports")


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new civic issue report.
    Supports multipart/form-data (with optional image file) and application/json.
    """
    content_type = request.headers.get("content-type", "")

    if "multipart/form-data" in content_type:
        form = await request.form()

        title = form.get("title")
        description = form.get("description")
        category = form.get("category")
        severity_val = form.get("severity") or ReportSeverity.MEDIUM.value
        latitude_str = form.get("latitude")
        longitude_str = form.get("longitude")
        address = form.get("address")
        ward = form.get("ward")
        locality = form.get("locality") or form.get("area")
        city = form.get("city")
        district = form.get("district")
        state = form.get("state")
        postal_code = form.get("postal_code")

        location_accuracy_val: Optional[float] = None
        acc_val = form.get("location_accuracy")
        if acc_val is not None:
            try:
                location_accuracy_val = float(acc_val)
            except (ValueError, TypeError):
                pass

        capture_timestamp_val: Optional[datetime] = None
        ts_val = form.get("capture_timestamp")
        if ts_val is not None:
            try:
                capture_timestamp_val = datetime.fromisoformat(str(ts_val).replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        if not description or latitude_str is None or longitude_str is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="description, latitude, and longitude are required.",
            )

        if not title and description:
            desc_text = str(description).strip()
            title = (desc_text[:57] + "...") if len(desc_text) > 60 else desc_text

        try:
            latitude = float(latitude_str)
            longitude = float(longitude_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid latitude or longitude values.",
            )

        try:
            severity = ReportSeverity(severity_val)
        except ValueError:
            severity = ReportSeverity.MEDIUM

        data = ReportCreate(
            title=str(title),
            description=str(description),
            category=str(category) if category else None,
            severity=severity,
            latitude=latitude,
            longitude=longitude,
            location_accuracy=location_accuracy_val,
            capture_timestamp=capture_timestamp_val,
            address=str(address) if address else None,
            locality=str(locality) if locality else None,
            city=str(city) if city else None,
            district=str(district) if district else None,
            state=str(state) if state else None,
            postal_code=str(postal_code) if postal_code else None,
            ward=str(ward) if ward else None,
        )

        image_file: Optional[Any] = None
        form_file = form.get("image")
        if hasattr(form_file, "filename") and getattr(form_file, "filename", None):
            image_file = form_file


        return await ReportService.create_report(
            db=db,
            reporter=current_user,
            data=data,
            image_file=image_file,
        )

    # application/json
    try:
        body = await request.json()
        data = ReportCreate(**body)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid report data: {e}",
        )

    return await ReportService.create_report(
        db=db,
        reporter=current_user,
        data=data,
        image_file=None,
    )


@router.get("", response_model=List[ReportResponse])
def get_reports(
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
    status_filter: Optional[str] = None,
    my_reports: bool = False,
    reporter_id: Optional[int] = None,
    include_rejected: bool = False,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_km: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    List civic reports with pagination, category/status filtering, proximity filtering,
    and current user's reports.
    """
    if include_rejected:
        if not current_user or current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can view rejected reports.",
            )

    if my_reports and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to view 'my_reports'.",
        )


    user_id = current_user.id if current_user else None

    return ReportService.get_reports(
        db=db,
        current_user_id=user_id,
        category=category,
        status_filter=status_filter,
        my_reports=my_reports,
        reporter_id=reporter_id,
        include_rejected=include_rejected,
        skip=skip,
        limit=limit,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
    )



@router.post("/analyze-ai", response_model=AIAnalysisResponse)
async def analyze_report_ai(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Provides real-time AI category recommendation for text description and/or image.
    Uses trained XLM-RoBERTa for text and civic_model.tflite for image.
    """
    content_type = request.headers.get("content-type", "")
    text: Optional[str] = None
    image_bytes: Optional[bytes] = None

    if "multipart/form-data" in content_type:
        form = await request.form()
        text_val = form.get("text") or form.get("description")
        if text_val:
            text = str(text_val)

        file = form.get("image")
        if hasattr(file, "filename") and getattr(file, "filename", None):
            image_bytes = await file.read()

    else:
        try:
            body = await request.json()
            text = body.get("text")
        except Exception:
            pass

    analysis = AIService.analyze_report(text=text, image_source=image_bytes)
    return analysis


@router.get("/{report_id}", response_model=ReportDetailResponse)
def get_report_detail(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Returns full details for a single report including comments, status logs,
    and media.
    """
    user_id = current_user.id if current_user else None
    report_dict = ReportService.get_report_by_id(db, report_id, current_user_id=user_id)
    if not report_dict:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found.",
        )
    return report_dict


@router.patch("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    data: ReportUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Updates report fields. Citizens can only update their own SUBMITTED reports.
    """
    return ReportService.update_report(
        db=db,
        report_id=report_id,
        user=current_user,
        data=data,
    )


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a report. Citizens can only delete their own reports; admins can delete any.
    """
    ReportService.delete_report(db=db, report_id=report_id, user=current_user)
    return {"message": "Report deleted successfully", "id": report_id}


@router.patch("/{report_id}/status", response_model=ReportResponse)
def update_report_status(
    report_id: int,
    status_in: StatusUpdateSchema,
    db: Session = Depends(get_db),
    authority: User = Depends(require_roles([UserRole.ADMIN, UserRole.MUNICIPALITY])),
):
    """
    Admin or municipal authority updates report status, department, and contractor assignment.
    Creates a new ReportStatusLog entry.
    """
    return ReportService.update_status(
        db=db,
        report_id=report_id,
        authority=authority,
        status_in=status_in,
    )


@router.post("/{report_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    report_id: int,
    comment_in: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Adds a comment to the report.
    """
    return ReportService.add_comment(
        db=db,
        report_id=report_id,
        user=current_user,
        content=comment_in.content,
    )


@router.get("/{report_id}/comments", response_model=List[CommentResponse])
def get_comments(
    report_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieves comments for a report.
    """
    return ReportService.get_comments(db=db, report_id=report_id)


@router.post("/{report_id}/upvote")
def toggle_upvote(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggles upvote for the current user on the specified report.
    Enforces one upvote per user.
    """
    return ReportService.toggle_upvote(
        db=db,
        report_id=report_id,
        user=current_user,
    )


@router.post("/{report_id}/moderate", response_model=ReportResponse, summary="Admin soft moderation of report")
def moderate_report(
    report_id: int,
    mod_in: ReportModerationRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles([UserRole.ADMIN])),
):
    """
    Moderates a report (REJECT or RESTORE).
    Rejecting soft-hides the report from public views and statistics while preserving audit history.
    """
    return CivicIssueService.moderate_report(
        db=db,
        report_id=report_id,
        action=mod_in.action,
        admin=admin,
        reason=mod_in.reason,
    )

