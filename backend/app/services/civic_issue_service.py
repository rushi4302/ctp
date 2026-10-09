"""
Civic Issue Service.

Manages the lifecycle of unique real-world Civic Issues and links citizen Reports
to them using explainable duplicate/related issue detection.
Enforces Role-Based Access Control (RBAC), audit logging, soft moderation,
and computes explainable Civic Health Scores.
"""

from datetime import datetime, timezone, timedelta
import logging
import re
from typing import List, Optional, Tuple, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.core.constants import (
    CivicIssueStatus,
    ModerationStatus,
    ReportSeverity,
    ReportStatus,
)
from app.core.roles import UserRole
from app.models.report import (
    CivicIssue,
    CivicIssueStatusLog,
    Report,
    ReportStatusLog,
)
from app.models.user import User
from app.services.location_service import LocationService
from app.services.ward_service import WardService

logger = logging.getLogger(__name__)

# Severity hierarchy for comparison
SEVERITY_WEIGHTS = {
    ReportSeverity.LOW.value: 1,
    ReportSeverity.MEDIUM.value: 2,
    ReportSeverity.HIGH.value: 3,
    ReportSeverity.CRITICAL.value: 4,
}

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "with", "is", "was", "are", "near", "by", "road", "street", "area",
    "please", "fix", "here", "there", "very", "big", "small"
}


class CivicIssueService:
    @staticmethod
    def _tokenize(text: str) -> set:
        """Tokenize text into lowercase alphanumeric words, filtering out short/stopwords."""
        if not text:
            return set()
        words = re.findall(r"[a-z0-9]+", text.lower())
        return {w for w in words if len(w) >= 3 and w not in STOP_WORDS}

    @classmethod
    def calculate_text_similarity(cls, text1: str, text2: str) -> float:
        """
        Explainable Jaccard similarity index between token sets of two descriptions.
        Range: 0.0 to 1.0.
        """
        tokens1 = cls._tokenize(text1)
        tokens2 = cls._tokenize(text2)
        if not tokens1 or not tokens2:
            return 0.0
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        return float(len(intersection)) / float(len(union)) if union else 0.0

    @classmethod
    def find_matching_issue(
        cls,
        db: Session,
        lat: float,
        lon: float,
        category: str,
        description: str,
        max_radius_meters: float = 75.0,
        min_similarity: float = 0.20,
    ) -> Optional[CivicIssue]:
        """
        Explainable duplicate/related issue detection.
        Searches active Civic Issues within max_radius_meters having compatible category
        and sufficient semantic similarity.
        """
        active_statuses = [
            CivicIssueStatus.PENDING.value,
            CivicIssueStatus.ASSIGNED.value,
            CivicIssueStatus.IN_PROGRESS.value,
        ]

        active_issues = (
            db.query(CivicIssue)
            .filter(CivicIssue.status.in_(active_statuses))
            .all()
        )

        best_match: Optional[CivicIssue] = None
        min_distance = float("inf")

        clean_cat = category.strip().lower()

        for issue in active_issues:
            # Category match or compatibility
            issue_cat = (issue.category or "").strip().lower()
            issue_ai_cat = (issue.ai_category or "").strip().lower()
            category_matches = (
                clean_cat == issue_cat
                or clean_cat == issue_ai_cat
                or (issue_cat in clean_cat or clean_cat in issue_cat)
            )
            if not category_matches:
                continue

            dist_m = LocationService.haversine_distance_meters(
                lat, lon, issue.latitude, issue.longitude
            )
            if dist_m > max_radius_meters:
                continue

            sim_score = cls.calculate_text_similarity(description, issue.description)

            # Match criteria:
            # 1. Distance <= 75m and token Jaccard similarity >= 0.20
            # 2. OR ultra-close proximity (<= 30m) with matching category
            if sim_score >= min_similarity or dist_m <= 30.0:
                if dist_m < min_distance:
                    min_distance = dist_m
                    best_match = issue

        return best_match

    @classmethod
    def attach_report_to_issue(
        cls,
        db: Session,
        report: Report,
        issue: CivicIssue,
    ) -> CivicIssue:
        """
        Attaches a citizen submission (Report) to an existing Civic Issue.
        Increments report count and records audit history.
        """
        now = datetime.now(timezone.utc)
        report.civic_issue_id = issue.id
        issue.report_count += 1
        issue.updated_at = now

        # Elevate severity if new report is more severe
        report_sev_weight = SEVERITY_WEIGHTS.get(report.severity, 2)
        issue_sev_weight = SEVERITY_WEIGHTS.get(issue.severity, 2)
        if report_sev_weight > issue_sev_weight:
            issue.severity = report.severity

        # Add status log entry to issue
        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=report.reporter_id,
            previous_status=issue.status,
            new_status=issue.status,
            comment=f"New citizen submission (Report #{report.id}) linked as duplicate/related issue.",
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def create_issue_from_report(
        cls,
        db: Session,
        report: Report,
        ward: Optional[str] = None,
    ) -> CivicIssue:
        """
        Creates a new Civic Issue representing a newly identified civic problem
        from an initial citizen Report submission.
        """
        now = datetime.now(timezone.utc)
        assigned_ward = ward or report.ward or WardService.assign_ward(report.latitude, report.longitude)

        issue = CivicIssue(
            title=report.title,
            description=report.description,
            category=report.category,
            status=CivicIssueStatus.PENDING.value,
            severity=report.severity,
            latitude=report.latitude,
            longitude=report.longitude,
            address=report.address,
            locality=report.locality,
            city=report.city,
            district=report.district,
            state=report.state,
            postal_code=report.postal_code,
            ward=assigned_ward,
            report_count=1,
            assigned_department_id=report.assigned_department_id,
            assigned_worker_id=None,
            ai_category=report.ai_category,
            ai_confidence=report.ai_confidence,
            created_at=now,
            updated_at=now,
        )
        db.add(issue)
        db.flush()

        # Link report
        report.civic_issue_id = issue.id

        # Status log
        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=report.reporter_id,
            previous_status="NONE",
            new_status=CivicIssueStatus.PENDING.value,
            comment=f"Civic Issue created from initial citizen Report #{report.id}.",
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def process_report_civic_issue_linkage(
        cls,
        db: Session,
        report: Report,
    ) -> Tuple[CivicIssue, bool]:
        """
        Checks for an existing active Civic Issue.
        If found, attaches the report. Otherwise creates a new Civic Issue.
        Returns (issue, is_duplicate).
        """
        matching_issue = cls.find_matching_issue(
            db=db,
            lat=report.latitude,
            lon=report.longitude,
            category=report.category,
            description=report.description,
        )

        if matching_issue:
            updated_issue = cls.attach_report_to_issue(db, report, matching_issue)
            return updated_issue, True

        new_issue = cls.create_issue_from_report(db, report)
        return new_issue, False

    @classmethod
    def get_civic_issues(
        cls,
        db: Session,
        status_filter: Optional[str] = None,
        category: Optional[str] = None,
        ward: Optional[str] = None,
        assigned_worker_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        radius_km: Optional[float] = None,
    ) -> List[CivicIssue]:
        """Queries civic issues with filters and optional proximity."""
        query = db.query(CivicIssue).options(
            joinedload(CivicIssue.assigned_worker),
            joinedload(CivicIssue.reports),
        )

        if status_filter and status_filter.strip():
            query = query.filter(CivicIssue.status == status_filter.strip())

        if category and category.strip():
            query = query.filter(CivicIssue.category == category.strip())

        if ward and ward.strip():
            query = query.filter(CivicIssue.ward == ward.strip())

        if assigned_worker_id:
            query = query.filter(CivicIssue.assigned_worker_id == assigned_worker_id)

        query = query.order_by(CivicIssue.created_at.desc())
        issues = query.offset(skip).limit(limit).all()

        if lat is not None and lon is not None and radius_km is not None:
            max_dist_m = radius_km * 1000.0
            filtered = []
            for issue in issues:
                dist = LocationService.haversine_distance_meters(lat, lon, issue.latitude, issue.longitude)
                if dist <= max_dist_m:
                    filtered.append(issue)
            issues = filtered

        return issues

    @classmethod
    def get_civic_issue_by_id(cls, db: Session, issue_id: int) -> Optional[CivicIssue]:
        """Fetches full Civic Issue with linked reports and status logs."""
        return (
            db.query(CivicIssue)
            .options(
                joinedload(CivicIssue.assigned_worker),
                joinedload(CivicIssue.reports).joinedload(Report.media),
                joinedload(CivicIssue.status_logs).joinedload(CivicIssueStatusLog.changed_by),
            )
            .filter(CivicIssue.id == issue_id)
            .first()
        )

    @classmethod
    def update_status(
        cls,
        db: Session,
        issue_id: int,
        new_status: str,
        user: User,
        comment: Optional[str] = None,
    ) -> CivicIssue:
        """
        Transitions Civic Issue status with RBAC enforcement and audit logging.
        """
        # RBAC Check first: Citizens cannot modify municipal workflow
        user_role = user.role
        if user_role in [UserRole.CITIZEN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens are not authorized to update municipal civic issue status.",
            )

        valid_statuses = [s.value for s in CivicIssueStatus]
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Civic Issue not found.")


        if user_role in [UserRole.FIELD_WORKER, UserRole.CONTRACTOR]:
            if issue.assigned_worker_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Field workers can only update civic issues assigned to them.",
                )
            allowed_worker_transitions = {
                CivicIssueStatus.ASSIGNED.value: [CivicIssueStatus.IN_PROGRESS.value],
                CivicIssueStatus.IN_PROGRESS.value: [CivicIssueStatus.RESOLVED.value],
            }
            if new_status not in allowed_worker_transitions.get(issue.status, []):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Workers cannot transition issue from {issue.status} to {new_status}.",
                )

        now = datetime.now(timezone.utc)
        prev_status = issue.status
        issue.status = new_status
        issue.updated_at = now

        if new_status == CivicIssueStatus.RESOLVED.value and not issue.resolved_at:
            issue.resolved_at = now
            # Synchronize linked active reports to RESOLVED
            for r in issue.reports:
                if r.moderation_status == ModerationStatus.ACTIVE.value:
                    r.status = ReportStatus.RESOLVED.value
                    r.updated_at = now
        elif new_status == CivicIssueStatus.CLOSED.value and not issue.closed_at:
            issue.closed_at = now

        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=user.id,
            previous_status=prev_status,
            new_status=new_status,
            comment=comment or f"Status changed from {prev_status} to {new_status}.",
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def assign_worker(
        cls,
        db: Session,
        issue_id: int,
        worker_id: int,
        authority: User,
        department_id: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> CivicIssue:
        """
        Assigns a Field Worker to a Civic Issue. Allowed for Municipality and Admin.
        """
        if authority.role not in [UserRole.ADMIN, UserRole.MUNICIPALITY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only municipal authorities or administrators can assign workers.",
            )

        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Civic Issue not found.")

        worker = db.query(User).filter(User.id == worker_id).first()
        if not worker:
            raise HTTPException(status_code=404, detail="Assigned worker user not found.")

        now = datetime.now(timezone.utc)
        prev_status = issue.status
        issue.assigned_worker_id = worker.id
        if department_id:
            issue.assigned_department_id = department_id.strip()

        # If issue was PENDING, automatically advance to ASSIGNED
        if issue.status == CivicIssueStatus.PENDING.value:
            issue.status = CivicIssueStatus.ASSIGNED.value

        issue.updated_at = now

        comment = f"Assigned to {worker.full_name} ({worker.email})."
        if notes:
            comment += f" Notes: {notes}"

        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=authority.id,
            previous_status=prev_status,
            new_status=issue.status,
            comment=comment,
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def update_category_and_severity(
        cls,
        db: Session,
        issue_id: int,
        authority: User,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> CivicIssue:
        """
        Allows Municipal Authority or Admin to correct category and severity.
        Preserves original AI prediction for full transparency and auditability.
        """
        if authority.role not in [UserRole.ADMIN, UserRole.MUNICIPALITY]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only authorities can modify category or severity.",
            )

        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Civic Issue not found.")

        now = datetime.now(timezone.utc)
        audit_changes = []

        if category and category.strip() and category.strip() != issue.category:
            audit_changes.append(f"Category changed from '{issue.category}' to '{category.strip()}'. Original AI: '{issue.ai_category}'")
            issue.category = category.strip()

        if severity and severity.strip() and severity.strip() != issue.severity:
            audit_changes.append(f"Severity changed from '{issue.severity}' to '{severity.strip()}'.")
            issue.severity = severity.strip()

        if audit_changes:
            issue.updated_at = now
            comment_text = " | ".join(audit_changes)
            if reason:
                comment_text += f" Reason: {reason}"
            log = CivicIssueStatusLog(
                civic_issue_id=issue.id,
                changed_by_id=authority.id,
                previous_status=issue.status,
                new_status=issue.status,
                comment=comment_text,
                created_at=now,
            )
            db.add(log)
            db.commit()
            db.refresh(issue)

        return issue

    @classmethod
    def resolve_with_evidence(
        cls,
        db: Session,
        issue_id: int,
        user: User,
        resolution_notes: str,
        resolution_evidence_url: Optional[str] = None,
        resolution_latitude: Optional[float] = None,
        resolution_longitude: Optional[float] = None,
        resolution_timestamp: Optional[datetime] = None,
    ) -> CivicIssue:
        """
        Marks an issue RESOLVED with proof notes and optional evidence media.
        """
        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Civic Issue not found.")

        if user.role not in [UserRole.ADMIN, UserRole.MUNICIPALITY, UserRole.FIELD_WORKER, UserRole.CONTRACTOR]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Citizens are not authorized to mark civic issues resolved.",
            )

        if user.role in [UserRole.FIELD_WORKER, UserRole.CONTRACTOR] and issue.assigned_worker_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Workers can only resolve tasks assigned to them.",
            )

        now = datetime.now(timezone.utc)
        prev_status = issue.status
        issue.status = CivicIssueStatus.RESOLVED.value
        issue.resolution_notes = resolution_notes.strip()
        if resolution_evidence_url:
            issue.resolution_evidence_url = resolution_evidence_url.strip()
        
        issue.resolution_latitude = resolution_latitude
        issue.resolution_longitude = resolution_longitude
        issue.resolution_timestamp = resolution_timestamp

        if resolution_latitude is not None and resolution_longitude is not None:
            dist = LocationService.haversine_distance_meters(
                resolution_latitude, resolution_longitude, issue.latitude, issue.longitude
            )
            issue.resolution_location_status = (
                LocationValidationStatus.VALID.value if dist <= 150 else LocationValidationStatus.MISMATCH.value
            )
        else:
            issue.resolution_location_status = "NO_LOCATION"

        issue.resolved_at = now
        issue.updated_at = now

        # Also update linked active reports
        for r in issue.reports:
            if r.moderation_status == ModerationStatus.ACTIVE.value:
                r.status = ReportStatus.RESOLVED.value
                r.updated_at = now

        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=user.id,
            previous_status=prev_status,
            new_status=CivicIssueStatus.RESOLVED.value,
            comment=f"Issue resolved. Evidence/Notes: {resolution_notes}",
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def request_reopen(
        cls,
        db: Session,
        issue_id: int,
        user: User,
    ) -> CivicIssue:
        """
        Citizen reports an issue is still not resolved. Changes status to REOPENED/PENDING.
        """
        issue = db.query(CivicIssue).filter(CivicIssue.id == issue_id).first()
        if not issue:
            raise HTTPException(status_code=404, detail="Civic Issue not found.")

        # Ensure the user has reported this issue or is an admin
        user_reported = any(r.reporter_id == user.id for r in issue.reports)
        if not user_reported and user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only reopen issues you have reported.",
            )

        if issue.status not in [CivicIssueStatus.RESOLVED.value, CivicIssueStatus.CLOSED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only resolved or closed issues can be reopened.",
            )

        now = datetime.now(timezone.utc)
        prev_status = issue.status
        issue.status = CivicIssueStatus.PENDING.value
        issue.updated_at = now

        for r in issue.reports:
            if r.moderation_status == ModerationStatus.ACTIVE.value:
                r.status = ReportStatus.IN_REVIEW.value
                r.updated_at = now

        log = CivicIssueStatusLog(
            civic_issue_id=issue.id,
            changed_by_id=user.id,
            previous_status=prev_status,
            new_status=CivicIssueStatus.PENDING.value,
            comment="Citizen reported issue is still not resolved. Reopened.",
            created_at=now,
        )
        db.add(log)
        db.commit()
        db.refresh(issue)
        return issue

    @classmethod
    def moderate_report(
        cls,
        db: Session,
        report_id: int,
        action: str,
        admin: User,
        reason: Optional[str] = None,
    ) -> Report:
        """
        Soft moderation of reports by Admin.
        Rejection hides the report from public views and statistics without hard-deleting.
        Preserves full audit trail.
        """
        if admin.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators are authorized to moderate reports.",
            )

        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found.")

        now = datetime.now(timezone.utc)
        action_upper = action.strip().upper()

        if action_upper == "REJECT":
            report.moderation_status = ModerationStatus.REJECTED.value
            report.status = ReportStatus.REJECTED.value
            report.rejected_at = now
            report.rejected_by_id = admin.id
            report.rejection_reason = reason or "Flagged as invalid or spam report."
            report.updated_at = now

            # Decrement report count on associated civic issue
            if report.civic_issue_id:
                issue = db.query(CivicIssue).filter(CivicIssue.id == report.civic_issue_id).first()
                if issue:
                    issue.report_count = max(0, issue.report_count - 1)
                    issue.updated_at = now

            status_log = ReportStatusLog(
                report_id=report.id,
                changed_by_id=admin.id,
                previous_status=report.status,
                new_status=ReportStatus.REJECTED.value,
                comment=f"Moderation REJECT by admin {admin.email}. Reason: {report.rejection_reason}",
                created_at=now,
            )
            db.add(status_log)

        elif action_upper == "RESTORE":
            report.moderation_status = ModerationStatus.ACTIVE.value
            report.status = ReportStatus.SUBMITTED.value
            report.rejected_at = None
            report.rejected_by_id = None
            report.rejection_reason = None
            report.updated_at = now

            if report.civic_issue_id:
                issue = db.query(CivicIssue).filter(CivicIssue.id == report.civic_issue_id).first()
                if issue:
                    issue.report_count += 1
                    issue.updated_at = now

            status_log = ReportStatusLog(
                report_id=report.id,
                changed_by_id=admin.id,
                previous_status=ReportStatus.REJECTED.value,
                new_status=ReportStatus.SUBMITTED.value,
                comment=f"Moderation RESTORE by admin {admin.email}.",
                created_at=now,
            )
            db.add(status_log)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown moderation action: {action}")

        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def get_transparency_statistics(cls, db: Session, ward: Optional[str] = None) -> Dict[str, Any]:
        """
        Public-safe civic transparency statistics.
        Excludes rejected/hidden reports and maintains distinction between
        citizen submissions (reports) and unique civic issues.
        """
        # Active reports only
        rep_query = db.query(Report).filter(Report.moderation_status == ModerationStatus.ACTIVE.value)
        issue_query = db.query(CivicIssue)

        if ward and ward.strip():
            rep_query = rep_query.filter(Report.ward == ward.strip())
            issue_query = issue_query.filter(CivicIssue.ward == ward.strip())

        total_reports = rep_query.count()
        total_issues = issue_query.count()

        pending_issues = issue_query.filter(CivicIssue.status == CivicIssueStatus.PENDING.value).count()
        assigned_issues = issue_query.filter(CivicIssue.status == CivicIssueStatus.ASSIGNED.value).count()
        in_progress_issues = issue_query.filter(CivicIssue.status == CivicIssueStatus.IN_PROGRESS.value).count()
        resolved_issues = issue_query.filter(CivicIssue.status == CivicIssueStatus.RESOLVED.value).count()
        closed_issues = issue_query.filter(CivicIssue.status == CivicIssueStatus.CLOSED.value).count()

        high_critical = issue_query.filter(
            CivicIssue.severity.in_([ReportSeverity.HIGH.value, ReportSeverity.CRITICAL.value])
        ).count()

        # Average resolution time in hours
        resolved_with_times = (
            issue_query.filter(
                CivicIssue.resolved_at.isnot(None),
                CivicIssue.created_at.isnot(None),
            )
            .all()
        )
        avg_res_time_hours: Optional[float] = None
        if resolved_with_times:
            total_seconds = sum(
                (issue.resolved_at - issue.created_at).total_seconds()
                for issue in resolved_with_times
                if issue.resolved_at and issue.created_at and issue.resolved_at >= issue.created_at
            )
            avg_res_time_hours = round(total_seconds / (len(resolved_with_times) * 3600.0), 1)

        # Category distribution of issues
        category_rows = (
            issue_query.with_entities(CivicIssue.category, func.count(CivicIssue.id))
            .group_by(CivicIssue.category)
            .all()
        )
        category_breakdown = {cat: count for cat, count in category_rows}

        # Ward distribution
        ward_rows = (
            issue_query.filter(CivicIssue.ward.isnot(None))
            .with_entities(CivicIssue.ward, func.count(CivicIssue.id))
            .group_by(CivicIssue.ward)
            .all()
        )
        ward_breakdown = {w: count for w, count in ward_rows}

        # Multi-report duplicate count
        multi_report_issues = issue_query.filter(CivicIssue.report_count > 1).count()

        return {
            "total_valid_reports": total_reports,
            "total_unique_civic_issues": total_issues,
            "pending_issues": pending_issues,
            "assigned_issues": assigned_issues,
            "in_progress_issues": in_progress_issues,
            "resolved_issues": resolved_issues,
            "closed_issues": closed_issues,
            "open_issues": pending_issues + assigned_issues + in_progress_issues,
            "high_critical_issues": high_critical,
            "average_resolution_hours": avg_res_time_hours,
            "category_distribution": category_breakdown,
            "ward_distribution": ward_breakdown,
            "multi_report_issues_count": multi_report_issues,
        }

    @classmethod
    def calculate_civic_health_score(cls, db: Session, ward: Optional[str] = None) -> Dict[str, Any]:
        """
        Explainable Civic Health Score (0 - 100).
        Formula:
          Civic Health Score =
              (Resolution Score * 0.30)
            + (Response/Handling * 0.20)
            + (Severity Health * 0.25)
            + (Pending Age Health * 0.15)
            + (Recurrence Health * 0.10)
        """
        issue_query = db.query(CivicIssue)
        if ward and ward.strip():
            issue_query = issue_query.filter(CivicIssue.ward == ward.strip())

        total_issues = issue_query.count()
        if total_issues == 0:
            return {
                "overall_score": 100.0,
                "rating": "EXCELLENT",
                "ward": ward,
                "total_issues_analyzed": 0,
                "components": {
                    "resolution_score": {"score": 100.0, "weight": 0.30, "description": "No civic issues reported."},
                    "response_score": {"score": 100.0, "weight": 0.20, "description": "All issues handled."},
                    "severity_health": {"score": 100.0, "weight": 0.25, "description": "No critical/high issues."},
                    "pending_age_health": {"score": 100.0, "weight": 0.15, "description": "No stale pending issues."},
                    "recurrence_health": {"score": 100.0, "weight": 0.10, "description": "Optimal civic recurrence."},
                },
            }

        resolved_count = issue_query.filter(
            CivicIssue.status.in_([CivicIssueStatus.RESOLVED.value, CivicIssueStatus.CLOSED.value])
        ).count()

        handled_count = issue_query.filter(
            CivicIssue.status.in_([
                CivicIssueStatus.ASSIGNED.value,
                CivicIssueStatus.IN_PROGRESS.value,
                CivicIssueStatus.RESOLVED.value,
                CivicIssueStatus.CLOSED.value,
            ])
        ).count()

        unresolved_critical = issue_query.filter(
            CivicIssue.status.in_([CivicIssueStatus.PENDING.value, CivicIssueStatus.ASSIGNED.value, CivicIssueStatus.IN_PROGRESS.value]),
            CivicIssue.severity == ReportSeverity.CRITICAL.value,
        ).count()

        unresolved_high = issue_query.filter(
            CivicIssue.status.in_([CivicIssueStatus.PENDING.value, CivicIssueStatus.ASSIGNED.value, CivicIssueStatus.IN_PROGRESS.value]),
            CivicIssue.severity == ReportSeverity.HIGH.value,
        ).count()

        # 1. Resolution Score (0 - 100): 30%
        resolution_score = round((resolved_count / total_issues) * 100.0, 1)

        # 2. Response / Handling Score (0 - 100): 20%
        response_score = round((handled_count / total_issues) * 100.0, 1)

        # 3. Severity Health (0 - 100): 25% (Penalizes unresolved high/critical issues)
        severity_penalty = (unresolved_critical * 25.0) + (unresolved_high * 10.0)
        severity_health = round(max(0.0, min(100.0, 100.0 - severity_penalty)), 1)

        # 4. Pending Age Health (0 - 100): 15% (Penalizes pending issues older than 7 days)
        cutoff_7d = datetime.now(timezone.utc) - timedelta(days=7)
        stale_pending = issue_query.filter(
            CivicIssue.status == CivicIssueStatus.PENDING.value,
            CivicIssue.created_at < cutoff_7d,
        ).count()
        pending_age_penalty = (stale_pending / total_issues) * 100.0
        pending_age_health = round(max(0.0, min(100.0, 100.0 - pending_age_penalty)), 1)

        # 5. Recurrence Health (0 - 100): 10%
        # Measures clustered duplicate report handling
        multi_reports = issue_query.filter(CivicIssue.report_count > 1).count()
        recurrence_ratio = multi_reports / total_issues
        recurrence_health = round(max(50.0, min(100.0, 100.0 - (recurrence_ratio * 30.0))), 1)

        # Weighted calculation
        overall_score = round(
            (resolution_score * 0.30)
            + (response_score * 0.20)
            + (severity_health * 0.25)
            + (pending_age_health * 0.15)
            + (recurrence_health * 0.10),
            1,
        )

        if overall_score >= 80.0:
            rating = "EXCELLENT"
        elif overall_score >= 65.0:
            rating = "GOOD"
        elif overall_score >= 50.0:
            rating = "AVERAGE"
        else:
            rating = "NEEDS_ATTENTION"

        return {
            "overall_score": overall_score,
            "rating": rating,
            "ward": ward,
            "total_issues_analyzed": total_issues,
            "components": {
                "resolution_score": {
                    "score": resolution_score,
                    "weight": 0.30,
                    "description": f"{resolved_count}/{total_issues} issues resolved or closed.",
                },
                "response_score": {
                    "score": response_score,
                    "weight": 0.20,
                    "description": f"{handled_count}/{total_issues} issues assigned or in progress.",
                },
                "severity_health": {
                    "score": severity_health,
                    "weight": 0.25,
                    "description": f"{unresolved_critical} critical and {unresolved_high} high priority unresolved issues.",
                },
                "pending_age_health": {
                    "score": pending_age_health,
                    "weight": 0.15,
                    "description": f"{stale_pending} pending issues older than 7 days.",
                },
                "recurrence_health": {
                    "score": recurrence_health,
                    "weight": 0.10,
                    "description": f"{multi_reports} issues with multiple citizen duplicate submissions.",
                },
            },
        }
