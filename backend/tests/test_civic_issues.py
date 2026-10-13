"""
Unit and Integration Tests for Civic Issue System, Duplicate Detection,
RBAC, Soft Moderation, Field Worker Workflow, and Civic Health Score.
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.constants import CivicIssueStatus, ModerationStatus, ReportSeverity, ReportStatus
from app.models.report import CivicIssue, Report
from app.models.user import User
from app.services.civic_issue_service import CivicIssueService
from app.services.storage_service import StorageService


def test_scenario_1_and_2_duplicate_civic_issue_detection(client: TestClient, citizen_headers: dict):
    """
    Scenario 1: Citizen submits a report -> Civic Issue is created.
    Scenario 2: Citizen B submits a duplicate/related issue nearby with same category ->
                Report attaches to existing Civic Issue, report_count increases to 2,
                and unique Civic Issue count remains 1.
    """
    # 1. Citizen A submits Report 1 (Pothole at 18.5204, 73.8567)
    payload1 = {
        "title": "Severe pothole near Deccan Gymkhana",
        "description": "Deep dangerous pothole on the main road near Deccan Gymkhana bus stop.",
        "category": "Pothole/Road Damage",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "severity": "HIGH",
    }
    r1 = client.post("/api/v1/reports", json=payload1, headers=citizen_headers)
    assert r1.status_code == 201
    data1 = r1.json()
    assert data1["id"] is not None
    civic_issue_id = data1.get("civic_issue_id")
    assert civic_issue_id is not None

    # Check the created Civic Issue
    issue_res = client.get(f"/api/v1/civic-issues/{civic_issue_id}", headers=citizen_headers)
    assert issue_res.status_code == 200
    issue_data = issue_res.json()
    assert issue_data["report_count"] == 1
    assert issue_data["status"] == CivicIssueStatus.PENDING.value

    # 2. Citizen B reports same pothole ~15 meters away
    payload2 = {
        "title": "Big pothole on road",
        "description": "Huge deep pothole causing traffic near Deccan Gymkhana bus stop.",
        "category": "Pothole/Road Damage",
        "latitude": 18.5205,  # ~11 meters north
        "longitude": 73.8567,
        "severity": "CRITICAL",
    }
    r2 = client.post("/api/v1/reports", json=payload2, headers=citizen_headers)
    assert r2.status_code == 201
    data2 = r2.json()
    assert data2["id"] is not None
    assert data2["id"] != data1["id"]

    # Must be linked to the same Civic Issue!
    assert data2["civic_issue_id"] == civic_issue_id
    assert data2["related_report_count"] == 2
    assert data2["is_synthetic"] is False

    # Civic Issue report_count should now be 2
    issue_res2 = client.get(f"/api/v1/civic-issues/{civic_issue_id}", headers=citizen_headers)
    assert issue_res2.status_code == 200
    issue_data2 = issue_res2.json()
    assert issue_data2["report_count"] == 2
    # Severity should have upgraded to CRITICAL because report 2 was CRITICAL
    assert issue_data2["severity"] == "CRITICAL"


def test_different_location_creates_new_civic_issue(client: TestClient, citizen_headers: dict):
    """
    Submitting an issue in a completely different location (e.g. Wagholi vs Deccan, ~15km away)
    creates a new distinct Civic Issue.
    """
    payload = {
        "title": "Garbage heap in Wagholi",
        "description": "Large garbage heap accumulating outside society gate in Wagholi.",
        "category": "Garbage",
        "latitude": 18.5793,
        "longitude": 73.9806,
        "severity": "MEDIUM",
    }
    res = client.post("/api/v1/reports", json=payload, headers=citizen_headers)
    assert res.status_code == 201
    data = res.json()
    new_issue_id = data["civic_issue_id"]
    assert new_issue_id is not None

    issue_res = client.get(f"/api/v1/civic-issues/{new_issue_id}", headers=citizen_headers)
    assert issue_res.status_code == 200
    assert issue_res.json()["report_count"] == 1


def test_admin_can_assign_department_without_field_worker(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Department assignment test",
            "description": "A road defect for testing municipal assignment.",
            "category": "Pothole/Road Damage",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "severity": "MEDIUM",
        },
        headers=citizen_headers,
    )
    assert created.status_code == 201
    issue_id = created.json()["civic_issue_id"]

    denied = client.patch(
        f"/api/v1/civic-issues/{issue_id}/assign",
        json={"department_id": "Roads Department"},
        headers=citizen_headers,
    )
    assert denied.status_code == 403

    assigned = client.patch(
        f"/api/v1/civic-issues/{issue_id}/assign",
        json={"department_id": "Roads Department", "notes": "Route to ward road crew"},
        headers=admin_headers,
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_department_id"] == "Roads Department"
    assert assigned.json()["status"] == CivicIssueStatus.ASSIGNED.value

    detail = client.get(f"/api/v1/civic-issues/{issue_id}", headers=citizen_headers)
    assert detail.status_code == 200
    assert detail.json()["status_logs"][-1]["comment"] == (
        "Assigned to department Roads Department. Notes: Route to ward road crew"
    )
    assert detail.json()["reports"][0]["assigned_department_id"] == "Roads Department"


def test_citizen_sees_admin_assignment_and_persisted_resolution(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
):
    submitted = client.post(
        "/api/v1/reports",
        json={
            "title": "End to end status flow",
            "description": "Broken footpath for assignment and resolution flow test.",
            "category": "Road Damage",
            "latitude": 18.531,
            "longitude": 73.861,
            "severity": "MEDIUM",
        },
        headers=citizen_headers,
    )
    assert submitted.status_code == 201
    report_id = submitted.json()["id"]
    issue_id = submitted.json()["civic_issue_id"]

    assigned = client.patch(
        f"/api/v1/civic-issues/{issue_id}/assign",
        json={"department_id": "Roads Department"},
        headers=admin_headers,
    )
    assert assigned.status_code == 200

    progress = client.patch(
        f"/api/v1/civic-issues/{issue_id}/status",
        json={"status": "IN_PROGRESS", "comment": "Repair crew dispatched"},
        headers=admin_headers,
    )
    assert progress.status_code == 200

    resolved = client.post(
        f"/api/v1/civic-issues/{issue_id}/resolve",
        data={"resolution_notes": "Footpath repaired and inspected."},
        headers=admin_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == CivicIssueStatus.RESOLVED.value

    citizen_view = client.get(f"/api/v1/reports/{report_id}", headers=citizen_headers)
    assert citizen_view.status_code == 200
    assert citizen_view.json()["status"] == ReportStatus.RESOLVED.value
    assert citizen_view.json()["assigned_department_id"] == "Roads Department"


def test_admin_resolution_multipart_persists_evidence_and_history(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
    sample_image_bytes: bytes,
):
    submitted = client.post(
        "/api/v1/reports",
        json={
            "title": "Synthetic resolution evidence integration test",
            "description": "A test-only road defect for image upload verification.",
            "category": "Pothole/Road Damage",
            "latitude": 18.521,
            "longitude": 73.857,
        },
        headers=citizen_headers,
    )
    assert submitted.status_code == 201
    issue_id = submitted.json()["civic_issue_id"]
    report_id = submitted.json()["id"]

    resolved = client.post(
        f"/api/v1/civic-issues/{issue_id}/resolve",
        headers=admin_headers,
        data={
            "resolution_notes": "Verified repair, this is test evidence.",
            "resolution_latitude": "18.5205",
            "resolution_longitude": "73.8571",
            "resolution_timestamp": datetime.now(timezone.utc).isoformat(),
        },
        files={"evidence_image": ("proof.jpg", sample_image_bytes, "image/jpeg")},
    )
    assert resolved.status_code == 200, resolved.text
    payload = resolved.json()
    assert payload["status"] == CivicIssueStatus.RESOLVED.value
    assert payload["resolution_evidence_url"].startswith("/uploads/")

    citizen_issue = client.get(f"/api/v1/civic-issues/{issue_id}", headers=citizen_headers)
    citizen_report = client.get(f"/api/v1/reports/{report_id}", headers=citizen_headers)
    assert citizen_issue.status_code == 200
    assert citizen_report.status_code == 200
    assert citizen_issue.json()["status"] == CivicIssueStatus.RESOLVED.value
    assert citizen_issue.json()["resolution_evidence_url"] == payload["resolution_evidence_url"]
    assert citizen_issue.json()["status_logs"][-1]["new_status"] == CivicIssueStatus.RESOLVED.value
    assert citizen_report.json()["status"] == ReportStatus.RESOLVED.value

    media = client.get(payload["resolution_evidence_url"])
    assert media.status_code == 200
    assert media.content == sample_image_bytes
    StorageService.delete_file(payload["resolution_evidence_url"].rsplit("/", 1)[-1])


def test_resolution_rejects_invalid_image_without_changing_status(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
):
    created = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Invalid evidence test",
            "description": "Test issue for invalid proof upload validation.",
            "category": "Streetlight Issue",
            "latitude": 18.522,
            "longitude": 73.858,
        },
    )
    issue_id = created.json()["civic_issue_id"]
    response = client.post(
        f"/api/v1/civic-issues/{issue_id}/resolve",
        headers=admin_headers,
        data={"resolution_notes": "Attempted invalid image upload."},
        files={"evidence_image": ("fake.jpg", b"not really a JPEG", "image/jpeg")},
    )
    assert response.status_code == 400
    current = client.get(f"/api/v1/civic-issues/{issue_id}", headers=citizen_headers)
    assert current.json()["status"] == CivicIssueStatus.PENDING.value


def test_citizen_cannot_upload_resolution_evidence(
    client: TestClient,
    citizen_headers: dict,
    sample_image_bytes: bytes,
):
    created = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Unauthorized evidence test",
            "description": "Test issue for authorization on resolution uploads.",
            "category": "Garbage",
            "latitude": 18.523,
            "longitude": 73.859,
        },
    )
    issue_id = created.json()["civic_issue_id"]
    before = {item.name for item in StorageService.get_upload_path().iterdir()}
    response = client.post(
        f"/api/v1/civic-issues/{issue_id}/resolve",
        headers=citizen_headers,
        data={"resolution_notes": "Citizen must not resolve."},
        files={"evidence_image": ("proof.jpg", sample_image_bytes, "image/jpeg")},
    )
    after = {item.name for item in StorageService.get_upload_path().iterdir()}
    assert response.status_code == 403
    assert after == before


def test_resolution_database_failure_rolls_back_and_removes_uploaded_file(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
    sample_image_bytes: bytes,
    monkeypatch: pytest.MonkeyPatch,
):
    created = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Resolution transaction failure test",
            "description": "Test issue for failed resolution transaction cleanup.",
            "category": "Drainage Problem",
            "latitude": 18.524,
            "longitude": 73.860,
        },
    )
    issue_id = created.json()["civic_issue_id"]
    before = {item.name for item in StorageService.get_upload_path().iterdir()}

    def fail_commit(**kwargs):
        raise RuntimeError("simulated database write failure")

    monkeypatch.setattr(CivicIssueService, "resolve_with_evidence", fail_commit)
    response = client.post(
        f"/api/v1/civic-issues/{issue_id}/resolve",
        headers=admin_headers,
        data={"resolution_notes": "This update should roll back."},
        files={"evidence_image": ("failure.jpg", sample_image_bytes, "image/jpeg")},
    )
    after = {item.name for item in StorageService.get_upload_path().iterdir()}
    assert response.status_code == 500
    assert response.json()["detail"] == "Resolution update could not be saved. Please retry."
    assert after == before


def test_scenario_3_false_report_soft_moderation(
    client: TestClient,
    citizen_headers: dict,
    admin_headers: dict,
):
    """
    Scenario 3: Admin reviews a false/spam report and rejects it.
    The report remains in the database with reason, is hidden from public active lists,
    and does not inflate public statistics.
    Admin can also restore it.
    """
    # Create report to moderate
    payload = {
        "title": "Fake broken streetlight report",
        "description": "Prank or spam test report submitted maliciously.",
        "category": "Streetlight Issue",
        "latitude": 18.5200,
        "longitude": 73.8500,
        "severity": "LOW",
    }
    create_res = client.post("/api/v1/reports", json=payload, headers=citizen_headers)
    assert create_res.status_code == 201
    report_id = create_res.json()["id"]

    # 1. Admin rejects the report with reason
    reject_res = client.post(
        f"/api/v1/reports/{report_id}/moderate",
        json={"action": "REJECT", "reason": "Verified spam/prank submission."},
        headers=admin_headers,
    )
    assert reject_res.status_code == 200
    mod_data = reject_res.json()
    assert mod_data["moderation_status"] == ModerationStatus.REJECTED.value
    assert mod_data["status"] == ReportStatus.REJECTED.value
    assert mod_data["rejection_reason"] == "Verified spam/prank submission."

    # 2. Check public reports listing (excludes rejected reports)
    public_reports = client.get("/api/v1/reports", headers=citizen_headers).json()
    assert not any(r["id"] == report_id for r in public_reports)

    # 3. Admin can still inspect rejected reports
    admin_reports = client.get("/api/v1/reports?include_rejected=true", headers=admin_headers).json()
    assert any(r["id"] == report_id and r["moderation_status"] == "REJECTED" for r in admin_reports)

    # 4. Admin restores the report
    restore_res = client.post(
        f"/api/v1/reports/{report_id}/moderate",
        json={"action": "RESTORE"},
        headers=admin_headers,
    )
    assert restore_res.status_code == 200
    assert restore_res.json()["moderation_status"] == ModerationStatus.ACTIVE.value

    # Now visible in public reports again
    public_reports_after = client.get("/api/v1/reports", headers=citizen_headers).json()
    assert any(r["id"] == report_id for r in public_reports_after)


def test_scenario_4_and_5_authority_and_field_worker_workflow(
    client: TestClient,
    citizen_headers: dict,
    municipality_headers: dict,
    field_worker_headers: dict,
    field_worker_user: User,
):
    """
    Scenario 4: Municipal Authority reviews Civic Issue, corrects severity, and assigns Field Worker.
    Scenario 5: Field Worker views assigned task, marks in progress, and submits resolution with evidence.
    """
    # 1. Citizen creates report
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Water leakage flooding road",
            "description": "Burst municipal pipeline flooding pedestrian walkway near Shivajinagar.",
            "category": "Water Leakage",
            "latitude": 18.5314,
            "longitude": 73.8446,
            "severity": "MEDIUM",
        },
        headers=citizen_headers,
    )
    assert create_res.status_code == 201
    issue_id = create_res.json()["civic_issue_id"]

    # 2. Municipal Authority corrects severity to HIGH
    corr_res = client.patch(
        f"/api/v1/civic-issues/{issue_id}/category-severity",
        json={"severity": "HIGH", "reason": "Pipe rupture poses immediate hazard."},
        headers=municipality_headers,
    )
    assert corr_res.status_code == 200
    assert corr_res.json()["severity"] == "HIGH"

    # 3. Municipal Authority assigns Field Worker
    assign_res = client.patch(
        f"/api/v1/civic-issues/{issue_id}/assign",
        json={"worker_id": field_worker_user.id, "department_id": "Water Supply Dept", "notes": "Urgent repair needed."},
        headers=municipality_headers,
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == CivicIssueStatus.ASSIGNED.value
    assert assign_res.json()["assigned_worker_id"] == field_worker_user.id

    # 4. Field Worker checks assigned issues
    worker_issues = client.get("/api/v1/field-worker/issues", headers=field_worker_headers).json()
    assert any(i["id"] == issue_id for i in worker_issues)

    # 5. Field Worker updates status to IN_PROGRESS
    progress_res = client.post(
        f"/api/v1/field-worker/issues/{issue_id}/progress",
        params={"progress_notes": "Excavation and pipe replacement started."},
        headers=field_worker_headers,
    )
    assert progress_res.status_code == 200
    assert progress_res.json()["status"] == CivicIssueStatus.IN_PROGRESS.value

    # 6. Field Worker resolves with notes and evidence photo
    resolve_res = client.post(
        f"/api/v1/field-worker/issues/{issue_id}/resolve",
        json={
            "resolution_notes": "Main valve repaired and road patched with quick-set cement.",
            "resolution_evidence_url": "/uploads/evidence_pipe_fixed.jpg",
        },
        headers=field_worker_headers,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == CivicIssueStatus.RESOLVED.value
    assert resolve_res.json()["resolution_notes"] is not None

    # Check status logs on detail view
    detail_res = client.get(f"/api/v1/civic-issues/{issue_id}", headers=municipality_headers)
    assert detail_res.status_code == 200
    logs = detail_res.json()["status_logs"]
    assert len(logs) >= 3  # Created -> Assigned -> In Progress -> Resolved


def test_scenario_6_unauthorized_access_rbac(
    client: TestClient,
    citizen_headers: dict,
    field_worker_headers: dict,
):
    """
    Scenario 6: Backend RBAC enforcement:
    - Citizen attempts to call Admin moderation -> 403 Forbidden.
    - Citizen attempts to assign worker or change issue status -> 403 Forbidden.
    - Field Worker attempts to moderate reports or assign workers -> 403 Forbidden.
    """
    # 1. Citizen cannot moderate
    res1 = client.post(
        "/api/v1/reports/1/moderate",
        json={"action": "REJECT"},
        headers=citizen_headers,
    )
    assert res1.status_code == 403

    # 2. Citizen cannot assign worker
    res2 = client.patch(
        "/api/v1/civic-issues/1/assign",
        json={"worker_id": 2},
        headers=citizen_headers,
    )
    assert res2.status_code == 403

    # 3. Citizen cannot update civic issue status directly
    res3 = client.patch(
        "/api/v1/civic-issues/1/status",
        json={"status": "RESOLVED"},
        headers=citizen_headers,
    )
    assert res3.status_code == 403

    # 4. Field Worker cannot moderate reports
    res4 = client.post(
        "/api/v1/reports/1/moderate",
        json={"action": "REJECT"},
        headers=field_worker_headers,
    )
    assert res4.status_code == 403

    # 5. Non-admin cannot request include_rejected=true
    res5 = client.get("/api/v1/reports?include_rejected=true", headers=citizen_headers)
    assert res5.status_code == 403


def test_public_transparency_and_civic_health_score(client: TestClient):
    """
    Verifies the public transparency endpoints:
    - /api/v1/transparency/stats
    - /api/v1/transparency/health-score
    - /api/v1/transparency/map
    """
    # 1. Public stats
    stats_res = client.get("/api/v1/transparency/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_valid_reports" in stats
    assert "total_unique_civic_issues" in stats
    assert "open_issues" in stats
    assert "category_distribution" in stats
    assert "severity_distribution" in stats
    assert 0.0 <= stats["resolution_rate"] <= 100.0

    # 2. Civic Health Score (0 - 100)
    score_res = client.get("/api/v1/transparency/health-score")
    assert score_res.status_code == 200
    score_data = score_res.json()
    if score_data["total_issues_analyzed"] < 5:
        assert score_data["overall_score"] is None
        assert score_data["rating"] == "INSUFFICIENT_DATA"
        assert score_data["components"] == {}
    else:
        assert 0.0 <= score_data["overall_score"] <= 100.0
        assert score_data["rating"] in ["EXCELLENT", "GOOD", "AVERAGE", "NEEDS_ATTENTION"]
        components = score_data["components"]
        assert "resolution_score" in components
        assert "response_score" in components
        assert "severity_health" in components
        assert "pending_age_health" in components
        assert "recurrence_health" in components

    # 3. Map points
    map_res = client.get("/api/v1/transparency/map")
    assert map_res.status_code == 200
    points = map_res.json()
    assert isinstance(points, list)
    if points:
        pt = points[0]
        assert "latitude" in pt
        assert "longitude" in pt
        assert "category" in pt
        assert "status" in pt


def test_public_map_filters_by_status_and_rejects_unknown_status(client, citizen_headers):
    created = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Map status filter test",
            "description": "A damaged road needs a repair near the public market.",
            "category": "Pothole/Road Damage",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
    )
    assert created.status_code == 201
    issue_id = created.json()["civic_issue_id"]

    pending = client.get("/api/v1/transparency/map?status_filter=PENDING")
    resolved = client.get("/api/v1/transparency/map?status_filter=RESOLVED")
    invalid = client.get("/api/v1/transparency/map?status_filter=NOT_A_STATUS")
    assert pending.status_code == 200
    assert any(point["id"] == issue_id for point in pending.json())
    assert all(point["id"] != issue_id for point in resolved.json())
    assert invalid.status_code == 422


def test_transparency_statistics_include_database_derived_locality_counts(client, citizen_headers):
    response = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "Locality breakdown verification",
            "description": "A blocked drain is holding water beside the community path.",
            "category": "Drainage Problem",
            "latitude": 18.58,
            "longitude": 73.98,
            "locality": "Wagholi",
        },
    )
    assert response.status_code == 201

    stats_response = client.get("/api/v1/transparency/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["locality_distribution"]["Wagholi"] == 1


def test_reopen_moves_linked_reports_back_to_submitted_and_rejects_invalid_transition(
    client: TestClient,
    citizen_headers: dict,
    municipality_headers: dict,
):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Reopen lifecycle test",
            "description": "A water leak still remains after repair.",
            "category": "Water Leakage",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    issue_id = created.json()["civic_issue_id"]
    report_id = created.json()["id"]

    resolved = client.patch(
        f"/api/v1/civic-issues/{issue_id}/status",
        json={"status": "RESOLVED"},
        headers=municipality_headers,
    )
    assert resolved.status_code == 200

    invalid = client.patch(
        f"/api/v1/civic-issues/{issue_id}/status",
        json={"status": "ASSIGNED"},
        headers=municipality_headers,
    )
    assert invalid.status_code == 409

    reopened = client.post(
        f"/api/v1/civic-issues/{issue_id}/reopen",
        headers=citizen_headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == CivicIssueStatus.PENDING.value
    report = client.get(f"/api/v1/reports/{report_id}", headers=citizen_headers).json()
    assert report["status"] == ReportStatus.SUBMITTED.value
    assert report["status_logs"][-1]["new_status"] == ReportStatus.SUBMITTED.value
