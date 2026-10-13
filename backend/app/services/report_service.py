from datetime import datetime, timezone
import logging
from typing import List, Optional, Tuple
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.core.constants import (
    CivicIssueStatus,
    LocationValidationStatus,
    ModerationStatus,
    ReportSeverity,
    ReportStatus,
)
from app.core.roles import UserRole
from app.models.report import Comment, Report, ReportMedia, ReportStatusLog, Upvote
from app.models.user import User
from app.schemas.report import ReportCreate, ReportUpdate, StatusUpdateSchema
from app.services.ai_service import AIService
from app.services.civic_issue_service import CivicIssueService
from app.services.exif_service import ExifService
from app.services.location_service import LocationService
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


class ReportService:
    @classmethod
    async def create_report(
        cls,
        db: Session,
        reporter: User,
        data: ReportCreate,
        image_file: Optional[UploadFile] = None,
    ) -> Report:
        """
        Creates a new civic report with image storage, EXIF extraction,
        location validation, and multimodal AI category prediction.
        """
        uploaded_media_data = None
        exif_lat = None
        exif_lon = None
        exif_timestamp = None
        image_path_for_ai = None

        if image_file and image_file.filename:
            uploaded_media_data = await StorageService.save_upload(image_file)
            image_path_for_ai = uploaded_media_data["file_path"]

            # Extract EXIF metadata
            exif_result = ExifService.extract_exif(uploaded_media_data["content_bytes"])
            if exif_result.get("has_gps"):
                exif_lat = exif_result.get("latitude")
                exif_lon = exif_result.get("longitude")
            exif_timestamp = exif_result.get("timestamp")

        # Location Validation
        loc_validation = LocationService.validate_location(
            submitted_lat=data.latitude,
            submitted_lon=data.longitude,
            exif_lat=exif_lat,
            exif_lon=exif_lon,
        )
        location_status = loc_validation["status"].value

        # AI Multimodal Analysis
        ai_result = AIService.analyze_report(
            text=f"{data.title}. {data.description}",
            image_source=image_path_for_ai,
        )

        ai_category = ai_result.get("suggested_category")
        ai_confidence = ai_result.get("suggested_confidence")

        # Category decision
        final_category = data.category
        if not final_category or not final_category.strip():
            final_category = ai_category or "Other"

        now = datetime.now(timezone.utc)
        report_title = (data.title or "").strip()
        if not report_title:
            desc_text = data.description.strip()
            report_title = (desc_text[:57] + "...") if len(desc_text) > 60 else desc_text

        report = Report(
            title=report_title,
            description=data.description.strip(),
            category=final_category,
            status=ReportStatus.SUBMITTED.value,
            severity=(data.severity.value if data.severity else ReportSeverity.MEDIUM.value),
            latitude=data.latitude,
            longitude=data.longitude,
            location_accuracy=data.location_accuracy,
            capture_timestamp=data.capture_timestamp,
            address=data.address,
            locality=data.locality,
            city=data.city,
            district=data.district,
            state=data.state,
            postal_code=data.postal_code,
            ward=data.ward,
            reporter_id=reporter.id,
            ai_category=ai_category,
            ai_confidence=ai_confidence,
            location_validation_status=location_status,
            created_at=now,
            updated_at=now,
        )

        db.add(report)
        db.flush()  # Populates report.id

        if uploaded_media_data:
            media = ReportMedia(
                report_id=report.id,
                file_url=uploaded_media_data["file_url"],
                file_name=uploaded_media_data["file_name"],
                file_type=uploaded_media_data["file_type"],
                file_size=uploaded_media_data["file_size"],
                exif_latitude=exif_lat,
                exif_longitude=exif_lon,
                exif_timestamp=exif_timestamp,
                capture_timestamp=data.capture_timestamp or exif_timestamp,
                created_at=now,
            )
            db.add(media)

        # Initial Status Log
        status_log = ReportStatusLog(
            report_id=report.id,
            changed_by_id=reporter.id,
            previous_status="NONE",
            new_status=ReportStatus.SUBMITTED.value,
            comment="Issue report submitted by citizen.",
            created_at=now,
        )
        db.add(status_log)

        # Civic Issue Linkage: duplicate/related detection or new issue creation
        issue, is_duplicate = CivicIssueService.process_report_civic_issue_linkage(db, report)
        logger.info(
            "Report %d linked to Civic Issue %d (duplicate=%s)",
            report.id,
            issue.id,
            is_duplicate,
        )

        db.commit()
        return cls.get_report_by_id(db, report.id, current_user_id=reporter.id)

    @classmethod
    def get_reports(
        cls,
        db: Session,
        current_user_id: Optional[int] = None,
        category: Optional[str] = None,
        status_filter: Optional[str] = None,
        my_reports: bool = False,
        reporter_id: Optional[int] = None,
        include_rejected: bool = False,
        skip: int = 0,
        limit: int = 50,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> List[dict]:
        query = db.query(Report).options(
            joinedload(Report.media),
            joinedload(Report.civic_issue),
        )

        if not include_rejected:
            query = query.filter(Report.moderation_status == ModerationStatus.ACTIVE.value)

        if my_reports and current_user_id:
            query = query.filter(Report.reporter_id == current_user_id)
        elif reporter_id:
            query = query.filter(Report.reporter_id == reporter_id)

        if category and category.strip():
            query = query.filter(Report.category == category.strip())

        if status_filter and status_filter.strip():
            query = query.filter(Report.status == status_filter.strip())

        query = query.order_by(Report.created_at.desc())
        all_reports = query.offset(skip).limit(limit).all()

        # Proximity filtering in memory if requested
        if lat is not None and lon is not None and radius_km is not None:
            max_dist_m = radius_km * 1000.0
            filtered = []
            for r in all_reports:
                dist = LocationService.haversine_distance_meters(lat, lon, r.latitude, r.longitude)
                if dist <= max_dist_m:
                    filtered.append(r)
            all_reports = filtered

        # Fetch upvote counts and user status
        results = []
        for r in all_reports:
            upvotes_cnt = db.query(func.count(Upvote.id)).filter(Upvote.report_id == r.id).scalar() or 0
            has_upvoted = False
            if current_user_id:
                has_upvoted = (
                    db.query(Upvote)
                    .filter(Upvote.report_id == r.id, Upvote.user_id == current_user_id)
                    .first()
                    is not None
                )

            data = {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "category": r.category,
                "status": r.status,
                "severity": r.severity,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "location_accuracy": r.location_accuracy,
                "capture_timestamp": r.capture_timestamp,
                "address": r.address,
                "locality": r.locality,
                "city": r.city,
                "district": r.district,
                "state": r.state,
                "postal_code": r.postal_code,
                "ward": r.ward,
                "reporter_id": r.reporter_id,
                "assigned_department_id": r.assigned_department_id,
                "contractor_id": r.contractor_id,
                "ai_category": r.ai_category,
                "ai_confidence": r.ai_confidence,
                "location_validation_status": r.location_validation_status,
                "civic_issue_id": r.civic_issue_id,
                "related_report_count": r.civic_issue.report_count if r.civic_issue else 1,
                "is_synthetic": r.title.startswith("[SYNTHETIC DEMO"),
                "moderation_status": r.moderation_status,
                "rejected_at": r.rejected_at,
                "rejection_reason": r.rejection_reason,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "upvotes_count": upvotes_cnt,
                "has_upvoted": has_upvoted,
                "media": r.media,
            }
            results.append(data)

        return results

    @classmethod
    def get_report_by_id(
        cls,
        db: Session,
        report_id: int,
        current_user_id: Optional[int] = None,
    ) -> Optional[dict]:
        report = (
            db.query(Report)
            .options(
                joinedload(Report.media),
                joinedload(Report.civic_issue),
                joinedload(Report.reporter),
                joinedload(Report.contractor),
                joinedload(Report.comments).joinedload(Comment.user),
                joinedload(Report.status_logs).joinedload(ReportStatusLog.changed_by),
            )
            .filter(Report.id == report_id)
            .first()
        )

        if not report:
            return None

        upvotes_cnt = db.query(func.count(Upvote.id)).filter(Upvote.report_id == report.id).scalar() or 0
        has_upvoted = False
        if current_user_id:
            has_upvoted = (
                db.query(Upvote)
                .filter(Upvote.report_id == report.id, Upvote.user_id == current_user_id)
                .first()
                is not None
            )

        data = {
            "id": report.id,
            "title": report.title,
            "description": report.description,
            "category": report.category,
            "status": report.status,
            "severity": report.severity,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "location_accuracy": report.location_accuracy,
            "capture_timestamp": report.capture_timestamp,
            "address": report.address,
            "locality": report.locality,
            "city": report.city,
            "district": report.district,
            "state": report.state,
            "postal_code": report.postal_code,
            "ward": report.ward,
            "reporter_id": report.reporter_id,
            "assigned_department_id": report.assigned_department_id,
            "contractor_id": report.contractor_id,
            "ai_category": report.ai_category,
            "ai_confidence": report.ai_confidence,
            "location_validation_status": report.location_validation_status,
            "civic_issue_id": report.civic_issue_id,
            "related_report_count": report.civic_issue.report_count if report.civic_issue else 1,
            "is_synthetic": report.title.startswith("[SYNTHETIC DEMO"),
            "moderation_status": report.moderation_status,
            "rejected_at": report.rejected_at,
            "rejection_reason": report.rejection_reason,
            "created_at": report.created_at,
            "updated_at": report.updated_at,
            "upvotes_count": upvotes_cnt,
            "has_upvoted": has_upvoted,
            "media": report.media,
            "reporter": report.reporter,
            "contractor": report.contractor,
            "comments": report.comments,
            "status_logs": report.status_logs,
        }
        return data

    @classmethod
    def update_report(
        cls,
        db: Session,
        report_id: int,
        user: User,
        data: ReportUpdate,
    ) -> Report:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        # Permissions: Citizen can only update own report if SUBMITTED
        if user.role == UserRole.CITIZEN:
            if report.reporter_id != user.id:
                raise HTTPException(status_code=403, detail="Not authorized to edit this report.")
            if report.status != ReportStatus.SUBMITTED.value:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot edit report once it has been verified or processed.",
                )

        if data.title is not None:
            report.title = data.title.strip()
        if data.description is not None:
            report.description = data.description.strip()
        if data.category is not None:
            report.category = data.category.strip()
        if data.severity is not None:
            report.severity = data.severity.value
        if data.address is not None:
            report.address = data.address
        if data.ward is not None:
            report.ward = data.ward

        report.updated_at = datetime.now(timezone.utc)
        db.commit()
        return cls.get_report_by_id(db, report.id, current_user_id=user.id)

    @classmethod
    def delete_report(cls, db: Session, report_id: int, user: User) -> bool:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        is_admin = user.role == UserRole.ADMIN
        is_owner = user.role == UserRole.CITIZEN and report.reporter_id == user.id
        if not (is_admin or is_owner):
            raise HTTPException(status_code=403, detail="Not authorized to delete this report.")
        if is_owner and report.status != ReportStatus.SUBMITTED.value:
            raise HTTPException(
                status_code=409,
                detail="A complaint can only be deleted before it is verified or processed.",
            )

        # Keep uploaded files until the database transaction commits. Report
        # relationships cascade to comments, votes, media rows, and status logs.
        filenames = [media.file_name for media in report.media]
        civic_issue = report.civic_issue
        db.delete(report)
        db.flush()

        # Civic issues are shared by related reports. Keep the aggregate while
        # any report remains, and remove it (including its timeline) when this
        # was the last linked report.
        if civic_issue is not None:
            remaining_count = (
                db.query(Report)
                .filter(Report.civic_issue_id == civic_issue.id)
                .count()
            )
            if remaining_count:
                civic_issue.report_count = remaining_count
            else:
                db.delete(civic_issue)

        db.commit()

        # File deletion is an external side effect; do it only after the
        # database commit so a failed commit never leaves a live row without
        # its image. A cleanup failure does not undo the persisted deletion.
        for filename in filenames:
            if not StorageService.delete_file(filename):
                logger.warning("Could not remove uploaded report image %s", filename)
        return True

    @classmethod
    def update_status(
        cls,
        db: Session,
        report_id: int,
        authority: User,
        status_in: StatusUpdateSchema,
    ) -> dict:
        """Authority/Admin endpoint to update report status and assignment."""
        if authority.role not in [UserRole.ADMIN, UserRole.MUNICIPALITY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only municipal authorities or administrators can update status.",
            )

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        old_status = report.status
        new_status = status_in.status.value

        allowed_report_transitions = {
            ReportStatus.SUBMITTED.value: {
                ReportStatus.VERIFIED.value,
                ReportStatus.IN_PROGRESS.value,
                ReportStatus.RESOLVED.value,
                ReportStatus.REJECTED.value,
                ReportStatus.FLAGGED.value,
            },
            ReportStatus.VERIFIED.value: {
                ReportStatus.IN_PROGRESS.value,
                ReportStatus.RESOLVED.value,
                ReportStatus.REJECTED.value,
                ReportStatus.FLAGGED.value,
            },
            ReportStatus.IN_PROGRESS.value: {
                ReportStatus.RESOLVED.value,
                ReportStatus.REJECTED.value,
                ReportStatus.FLAGGED.value,
            },
            ReportStatus.RESOLVED.value: {ReportStatus.IN_PROGRESS.value},
            ReportStatus.REJECTED.value: {ReportStatus.SUBMITTED.value},
            ReportStatus.FLAGGED.value: {
                ReportStatus.VERIFIED.value,
                ReportStatus.REJECTED.value,
            },
        }
        if new_status == old_status:
            return cls.get_report_by_id(db, report.id, current_user_id=authority.id)
        if new_status not in allowed_report_transitions.get(old_status, set()):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot transition report from {old_status} to {new_status}.",
            )

        report.status = new_status
        if status_in.assigned_department_id is not None:
            report.assigned_department_id = status_in.assigned_department_id
        if status_in.contractor_id is not None:
            report.contractor_id = status_in.contractor_id

        now = datetime.now(timezone.utc)
        report.updated_at = now

        log = ReportStatusLog(
            report_id=report.id,
            changed_by_id=authority.id,
            previous_status=old_status,
            new_status=new_status,
            comment=status_in.comment or f"Status transitioned from {old_status} to {new_status}.",
            created_at=now,
        )
        db.add(log)

        # Keep the shared issue lifecycle in step with report workflow. A
        # linked issue can only move forward here; reopen is handled by the
        # dedicated civic issue endpoint so its status history stays explicit.
        issue = report.civic_issue
        if issue is not None:
            target_issue_status = {
                ReportStatus.VERIFIED.value: CivicIssueStatus.ASSIGNED.value,
                ReportStatus.IN_PROGRESS.value: CivicIssueStatus.IN_PROGRESS.value,
                ReportStatus.RESOLVED.value: CivicIssueStatus.RESOLVED.value,
            }.get(new_status)
            if new_status == ReportStatus.REJECTED.value:
                remaining_active_reports = (
                    db.query(Report)
                    .filter(
                        Report.civic_issue_id == issue.id,
                        Report.moderation_status == ModerationStatus.ACTIVE.value,
                        Report.status.notin_(
                            [ReportStatus.REJECTED.value, ReportStatus.FLAGGED.value]
                        ),
                    )
                    .count()
                )
                if remaining_active_reports == 0:
                    target_issue_status = CivicIssueStatus.CLOSED.value

            if target_issue_status is not None:
                issue_order = {
                    CivicIssueStatus.PENDING.value: 0,
                    CivicIssueStatus.ASSIGNED.value: 1,
                    CivicIssueStatus.IN_PROGRESS.value: 2,
                    CivicIssueStatus.RESOLVED.value: 3,
                    CivicIssueStatus.CLOSED.value: 4,
                }
                if issue_order.get(target_issue_status, 0) > issue_order.get(issue.status, 0):
                    CivicIssueService.update_status(
                        db=db,
                        issue_id=issue.id,
                        new_status=target_issue_status,
                        user=authority,
                        comment=status_in.comment,
                    )
        db.commit()
        return cls.get_report_by_id(db, report.id, current_user_id=authority.id)

    @classmethod
    def add_comment(
        cls,
        db: Session,
        report_id: int,
        user: User,
        content: str,
    ) -> Comment:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        comment = Comment(
            report_id=report_id,
            user_id=user.id,
            content=content.strip(),
            created_at=datetime.now(timezone.utc),
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        comment.user = user
        return comment

    @classmethod
    def get_comments(cls, db: Session, report_id: int) -> List[Comment]:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        return (
            db.query(Comment)
            .options(joinedload(Comment.user))
            .filter(Comment.report_id == report_id)
            .order_by(Comment.created_at.asc())
            .all()
        )

    @classmethod
    def toggle_upvote(cls, db: Session, report_id: int, user: User) -> dict:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        existing = (
            db.query(Upvote)
            .filter(Upvote.report_id == report_id, Upvote.user_id == user.id)
            .first()
        )
        if existing:
            db.delete(existing)
            db.commit()
            upvoted = False
        else:
            upvote = Upvote(
                report_id=report_id,
                user_id=user.id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(upvote)
            db.commit()
            upvoted = True

        total_upvotes = db.query(func.count(Upvote.id)).filter(Upvote.report_id == report_id).scalar() or 0
        return {"report_id": report_id, "has_upvoted": upvoted, "total_upvotes": total_upvotes}

    @classmethod
    def get_statistics(cls, db: Session) -> dict:
        total = db.query(func.count(Report.id)).scalar() or 0
        submitted = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.SUBMITTED.value).scalar() or 0
        verified = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.VERIFIED.value).scalar() or 0
        in_progress = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.IN_PROGRESS.value).scalar() or 0
        resolved = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.RESOLVED.value).scalar() or 0
        rejected = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.REJECTED.value).scalar() or 0
        flagged = db.query(func.count(Report.id)).filter(Report.status == ReportStatus.FLAGGED.value).scalar() or 0

        by_category = (
            db.query(Report.category, func.count(Report.id))
            .group_by(Report.category)
            .all()
        )

        return {
            "total_reports": total,
            "submitted": submitted,
            "verified": verified,
            "in_progress": in_progress,
            "resolved": resolved,
            "rejected": rejected,
            "flagged": flagged,
            "by_category": {cat: count for cat, count in by_category},
        }
