from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    CivicIssueStatus,
    LocationValidationStatus,
    ModerationStatus,
    ReportSeverity,
    ReportStatus,
)
from app.database.base import Base


class CivicIssue(Base):
    __tablename__ = "civic_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default=CivicIssueStatus.PENDING.value,
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        default=ReportSeverity.MEDIUM.value,
        nullable=False,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ward: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)

    report_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    assigned_department_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_worker_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolution_evidence_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resolution_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    resolution_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_location_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    assigned_worker = relationship("User", foreign_keys=[assigned_worker_id])
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="civic_issue")
    status_logs: Mapped[List["CivicIssueStatusLog"]] = relationship(
        "CivicIssueStatusLog",
        back_populates="civic_issue",
        cascade="all, delete-orphan",
        order_by="CivicIssueStatusLog.created_at.asc()",
    )

    @property
    def is_synthetic(self) -> bool:
        """Keep the existing title marker as internal synthetic-record metadata."""
        return self.title.startswith("[SYNTHETIC DEMO")


class CivicIssueStatusLog(Base):
    __tablename__ = "civic_issue_status_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    civic_issue_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("civic_issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    civic_issue = relationship("CivicIssue", back_populates="status_logs")
    changed_by = relationship("User")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    civic_issue_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("civic_issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    status: Mapped[str] = mapped_column(
        String(50),
        default=ReportStatus.SUBMITTED.value,
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(50),
        default=ReportSeverity.MEDIUM.value,
        nullable=False,
        index=True,
    )

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    location_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    capture_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    locality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    district: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ward: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    reporter_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assigned_department_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contractor_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    ai_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_validation_status: Mapped[str] = mapped_column(
        String(50),
        default=LocationValidationStatus.VALID.value,
        nullable=False,
    )

    moderation_status: Mapped[str] = mapped_column(
        String(50),
        default=ModerationStatus.ACTIVE.value,
        nullable=False,
        index=True,
    )
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejected_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id])
    contractor = relationship("User", foreign_keys=[contractor_id])
    rejected_by = relationship("User", foreign_keys=[rejected_by_id])
    civic_issue = relationship("CivicIssue", back_populates="reports")
    media: Mapped[List["ReportMedia"]] = relationship(
        "ReportMedia",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="Comment.created_at.asc()",
    )
    upvotes: Mapped[List["Upvote"]] = relationship(
        "Upvote",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    status_logs: Mapped[List["ReportStatusLog"]] = relationship(
        "ReportStatusLog",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportStatusLog.created_at.asc()",
    )



class ReportMedia(Base):
    __tablename__ = "report_media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    exif_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exif_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exif_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    capture_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    report = relationship("Report", back_populates="media")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    report = relationship("Report", back_populates="comments")
    user = relationship("User")


class Upvote(Base):
    __tablename__ = "upvotes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("report_id", "user_id", name="uq_report_user_upvote"),
    )

    report = relationship("Report", back_populates="upvotes")
    user = relationship("User")


class ReportStatusLog(Base):
    __tablename__ = "report_status_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_status: Mapped[str] = mapped_column(String(50), nullable=False)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    report = relationship("Report", back_populates="status_logs")
    changed_by = relationship("User")
