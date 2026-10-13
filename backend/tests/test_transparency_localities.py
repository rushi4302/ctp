from datetime import datetime, timezone

from app.core.constants import CivicIssueStatus, ReportSeverity
from app.models.report import CivicIssue
from app.schemas.civic_issue import CivicIssueResponse


def _add_issue(db, *, status: str, locality: str = "Wagholi") -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(
        CivicIssue(
            title="Issue for locality score test",
            description="Test-only issue record",
            category="Other",
            status=status,
            severity=ReportSeverity.LOW.value,
            latitude=18.58,
            longitude=73.98,
            locality=locality,
            report_count=1,
            created_at=now,
            updated_at=now,
        )
    )
    db.flush()


def test_locality_statistics_and_score_use_only_locality_issue_records(client, db):
    for status in (
        CivicIssueStatus.RESOLVED.value,
        CivicIssueStatus.RESOLVED.value,
        CivicIssueStatus.CLOSED.value,
        CivicIssueStatus.ASSIGNED.value,
        CivicIssueStatus.PENDING.value,
    ):
        _add_issue(db, status=status)
    _add_issue(db, status=CivicIssueStatus.PENDING.value, locality="Kharadi")

    stats = client.get("/api/v1/transparency/stats", params={"locality": "Wagholi"})
    assert stats.status_code == 200
    data = stats.json()
    assert data["total_unique_civic_issues"] == 5
    assert data["resolved_issues"] == 2
    assert data["closed_issues"] == 1
    assert data["pending_issues"] == 1
    assert data["assigned_issues"] == 1
    assert data["in_progress_issues"] == 0
    assert data["open_issues"] == 2
    assert data["resolution_rate"] == 60.0

    score = client.get("/api/v1/transparency/health-score", params={"locality": "Wagholi"})
    assert score.status_code == 200
    score_data = score.json()
    assert score_data["locality"] == "Wagholi"
    assert score_data["total_issues_analyzed"] == 5
    assert score_data["overall_score"] == 84.0
    assert score_data["components"]["resolution_score"]["score"] == 60.0

    insufficient = client.get(
        "/api/v1/transparency/health-score", params={"locality": "Kharadi"}
    )
    assert insufficient.status_code == 200
    assert insufficient.json()["overall_score"] is None
    assert insufficient.json()["rating"] == "INSUFFICIENT_DATA"
    assert insufficient.json()["total_issues_analyzed"] == 1


def test_transparency_rejects_combined_ward_and_locality_filters(client):
    response = client.get(
        "/api/v1/transparency/health-score",
        params={"ward": "Ward A", "locality": "Wagholi"},
    )
    assert response.status_code == 422


def test_civic_issue_response_preserves_synthetic_marker_as_metadata(db):
    _add_issue(db, status=CivicIssueStatus.PENDING.value)
    issue = db.query(CivicIssue).one()
    issue.title = "[SYNTHETIC DEMO DATASET V2 001] Blocked roadside drain"
    db.flush()

    response = CivicIssueResponse.model_validate(issue)
    assert response.is_synthetic is True
    assert response.title.startswith("[SYNTHETIC DEMO")
