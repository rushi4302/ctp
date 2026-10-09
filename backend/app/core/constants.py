from enum import Enum


class ReportStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    VERIFIED = "VERIFIED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    FLAGGED = "FLAGGED"


class ReportSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class LocationValidationStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    MISSING_METADATA = "MISSING_METADATA"
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"


class CivicCategory(str, Enum):
    POTHOLE_ROAD_DAMAGE = "Pothole/Road Damage"
    GARBAGE = "Garbage"
    WATER_LEAKAGE = "Water Leakage"
    STREETLIGHT_ISSUE = "Streetlight Issue"
    DRAINAGE_PROBLEM = "Drainage Problem"
    TRAFFIC_ISSUE = "Traffic Issue"
    OTHER = "Other"


class CivicIssueStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ModerationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"

