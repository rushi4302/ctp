import io
from fastapi import status
from app.core.roles import UserRole
from app.core.security import create_access_token, hash_password
from app.models.report import CivicIssue, Comment, Report, ReportStatusLog, Upvote
from app.models.user import User


def test_create_report_json(client, citizen_headers, citizen_user):
    payload = {
        "title": "Large pothole on FC Road",
        "description": "Deep dangerous pothole near the traffic junction.",
        "category": "Pothole/Road Damage",
        "severity": "HIGH",
        "latitude": 18.5204,
        "longitude": 73.8567,
        "address": "FC Road, Shivajinagar",
        "ward": "Ward 5",
    }
    response = client.post("/api/v1/reports", json=payload, headers=citizen_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["reporter_id"] == citizen_user.id
    assert data["status"] == "SUBMITTED"
    assert data["location_validation_status"] == "MISSING_METADATA"
    assert "id" in data


def test_report_response_labels_synthetic_demo_records(client, citizen_headers):
    response = client.post(
        "/api/v1/reports",
        headers=citizen_headers,
        json={
            "title": "[SYNTHETIC DEMO TEST] Example",
            "description": "Synthetic record to verify explicit demo labeling.",
            "category": "Garbage",
            "latitude": 18.5793,
            "longitude": 73.9828,
        },
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["is_synthetic"] is True


def test_create_report_multipart_with_image(client, citizen_headers, citizen_user, sample_image_bytes):
    data = {
        "title": "Overflowing Garbage Dumpster",
        "description": "Garbage has not been collected for three days.",
        "category": "Garbage",
        "severity": "MEDIUM",
        "latitude": 18.5310,
        "longitude": 73.8440,
        "address": "Model Colony",
    }
    files = {
        "image": ("trash.jpg", io.BytesIO(sample_image_bytes), "image/jpeg"),
    }
    response = client.post(
        "/api/v1/reports",
        data=data,
        files=files,
        headers=citizen_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()
    assert res_data["title"] == data["title"]
    assert len(res_data["media"]) == 1
    assert "file_url" in res_data["media"][0]


def test_create_report_with_structured_metadata(client, citizen_headers, citizen_user, sample_image_bytes):
    data = {
        "title": "Road crater near college",
        "description": "Severe road crater near campus entrance.",
        "category": "Pothole/Road Damage",
        "severity": "HIGH",
        "latitude": 18.5793,
        "longitude": 73.9821,
        "location_accuracy": "7.5",
        "capture_timestamp": "2026-09-25T12:30:45+05:30",
        "address": "GH Raisoni College, Wagholi, Pune, Maharashtra 412207",
        "locality": "Wagholi",
        "city": "Pune",
        "district": "Pune",
        "state": "Maharashtra",
        "postal_code": "412207",
    }
    files = {
        "image": ("road_crater.jpg", io.BytesIO(sample_image_bytes), "image/jpeg"),
    }
    response = client.post(
        "/api/v1/reports",
        data=data,
        files=files,
        headers=citizen_headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    res_data = response.json()
    assert res_data["title"] == data["title"]
    assert res_data["latitude"] == 18.5793
    assert res_data["longitude"] == 73.9821
    assert res_data["location_accuracy"] == 7.5
    assert res_data["capture_timestamp"] is not None
    assert res_data["locality"] == "Wagholi"
    assert res_data["city"] == "Pune"
    assert res_data["state"] == "Maharashtra"
    assert res_data["postal_code"] == "412207"
    assert len(res_data["media"]) == 1
    assert res_data["media"][0]["capture_timestamp"] is not None



def test_get_reports_list(client, citizen_headers):
    # Create two reports
    client.post(
        "/api/v1/reports",
        json={
            "title": "Streetlight broken",
            "description": "Streetlight off at night",
            "category": "Streetlight Issue",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )

    response = client.get("/api/v1/reports")
    assert response.status_code == status.HTTP_200_OK
    reports = response.json()
    assert len(reports) >= 1

    # Filter by category
    res_filtered = client.get("/api/v1/reports?category=Streetlight Issue")
    assert res_filtered.status_code == status.HTTP_200_OK
    assert all(r["category"] == "Streetlight Issue" for r in res_filtered.json())


def test_my_reports_filter(client, citizen_headers, admin_headers):
    client.post(
        "/api/v1/reports",
        json={
            "title": "Citizen own report",
            "description": "Created by citizen",
            "category": "Other",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )

    response = client.get("/api/v1/reports?my_reports=true", headers=citizen_headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) >= 1

    # Without auth, my_reports=true must return 401
    unauth_resp = client.get("/api/v1/reports?my_reports=true")
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_report_detail_and_status_logs(client, citizen_headers):
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Water leakage in sector 3",
            "description": "Clean drinking water leaking on road",
            "category": "Water Leakage",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )
    report_id = create_res.json()["id"]

    detail_res = client.get(f"/api/v1/reports/{report_id}", headers=citizen_headers)
    assert detail_res.status_code == status.HTTP_200_OK
    data = detail_res.json()
    assert data["id"] == report_id
    assert "email" not in data["reporter"]
    assert len(data["status_logs"]) >= 1
    assert data["status_logs"][0]["new_status"] == "SUBMITTED"


def test_update_report_by_citizen(client, citizen_headers):
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Original Title",
            "description": "Original Description",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )
    report_id = create_res.json()["id"]

    update_res = client.patch(
        f"/api/v1/reports/{report_id}",
        json={"title": "Updated Title", "description": "Updated Description"},
        headers=citizen_headers,
    )
    assert update_res.status_code == status.HTTP_200_OK
    assert update_res.json()["title"] == "Updated Title"


def test_admin_update_status_and_logs(client, citizen_headers, municipality_headers, admin_headers):
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Clogged Drain",
            "description": "Rainwater overflowing onto footpath",
            "category": "Drainage Problem",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )
    report_id = create_res.json()["id"]

    # Citizen cannot change status
    cit_status_res = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "VERIFIED", "comment": "Trying to self-verify"},
        headers=citizen_headers,
    )
    assert cit_status_res.status_code == status.HTTP_403_FORBIDDEN

    # Municipality updates status to VERIFIED
    muni_res = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "VERIFIED", "comment": "Officer verified issue on-site."},
        headers=municipality_headers,
    )
    assert muni_res.status_code == status.HTTP_200_OK
    assert muni_res.json()["status"] == "VERIFIED"

    # Once verified, citizen cannot modify report content
    cit_edit_res = client.patch(
        f"/api/v1/reports/{report_id}",
        json={"title": "Should fail because report is VERIFIED"},
        headers=citizen_headers,
    )
    assert cit_edit_res.status_code == status.HTTP_400_BAD_REQUEST

    # Admin updates to RESOLVED
    admin_res = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "RESOLVED", "comment": "Drain cleaned and flushed."},
        headers=admin_headers,
    )
    assert admin_res.status_code == status.HTTP_200_OK
    assert admin_res.json()["status"] == "RESOLVED"

    # Check status logs
    detail_res = client.get(f"/api/v1/reports/{report_id}")
    logs = detail_res.json()["status_logs"]
    statuses = [log["new_status"] for log in logs]
    assert "SUBMITTED" in statuses
    assert "VERIFIED" in statuses
    assert "RESOLVED" in statuses


def test_report_status_rejects_invalid_transition(client, citizen_headers, admin_headers):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Report transition validation",
            "description": "Check report workflow rules.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    report_id = created.json()["id"]
    assert client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "RESOLVED"},
        headers=admin_headers,
    ).status_code == status.HTTP_200_OK
    invalid = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "VERIFIED"},
        headers=admin_headers,
    )
    assert invalid.status_code == status.HTTP_409_CONFLICT


def test_comments_flow(client, citizen_headers, municipality_headers):
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Comment test report",
            "description": "Report for testing comments",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )
    report_id = create_res.json()["id"]

    # Citizen adds comment
    c1 = client.post(
        f"/api/v1/reports/{report_id}/comments",
        json={"content": "Please prioritize this area."},
        headers=citizen_headers,
    )
    assert c1.status_code == status.HTTP_201_CREATED
    assert c1.json()["content"] == "Please prioritize this area."

    # Municipality replies
    c2 = client.post(
        f"/api/v1/reports/{report_id}/comments",
        json={"content": "Work order has been dispatched."},
        headers=municipality_headers,
    )
    assert c2.status_code == status.HTTP_201_CREATED

    # List comments
    list_res = client.get(f"/api/v1/reports/{report_id}/comments")
    assert list_res.status_code == status.HTTP_200_OK
    assert len(list_res.json()) == 2


def test_owner_can_delete_report_and_cascaded_data(client, db, citizen_headers, citizen_user):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Delete flow test",
            "description": "A report created to verify owner deletion.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    assert created.status_code == status.HTTP_201_CREATED
    report_id = created.json()["id"]
    civic_issue_id = created.json()["civic_issue_id"]

    comment_response = client.post(
        f"/api/v1/reports/{report_id}/comments",
        json={"content": "Test comment to cascade."},
        headers=citizen_headers,
    )
    assert comment_response.status_code == status.HTTP_201_CREATED
    assert client.post(f"/api/v1/reports/{report_id}/upvote", headers=citizen_headers).status_code == 200

    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=citizen_headers)
    assert deleted.status_code == status.HTTP_200_OK
    assert client.get(f"/api/v1/reports/{report_id}", headers=citizen_headers).status_code == status.HTTP_404_NOT_FOUND
    assert db.query(Report).filter(Report.id == report_id).count() == 0
    assert db.query(Comment).filter(Comment.report_id == report_id).count() == 0
    assert db.query(Upvote).filter(Upvote.report_id == report_id).count() == 0
    assert db.query(ReportStatusLog).filter(ReportStatusLog.report_id == report_id).count() == 0
    assert db.query(CivicIssue).filter(CivicIssue.id == civic_issue_id).count() == 0


def test_delete_report_is_owner_or_admin_only(client, db, citizen_headers, citizen_user, admin_headers):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Authorization delete test",
            "description": "Only the owner or admin should delete this report.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    report_id = created.json()["id"]

    other_user = User(
        email="other-delete-user@test.civic.org",
        full_name="Other Citizen",
        hashed_password=hash_password("Password123!"),
        role=UserRole.CITIZEN,
        is_active=True,
    )
    db.add(other_user)
    db.commit()
    other_token = create_access_token({"sub": str(other_user.id), "role": other_user.role.value})
    other_headers = {"Authorization": f"Bearer {other_token}"}

    assert client.delete(f"/api/v1/reports/{report_id}", headers=other_headers).status_code == status.HTTP_403_FORBIDDEN
    assert client.delete(f"/api/v1/reports/{report_id}", headers=admin_headers).status_code == status.HTTP_200_OK
    assert client.delete(f"/api/v1/reports/{report_id}", headers=citizen_headers).status_code == status.HTTP_404_NOT_FOUND


def test_owner_cannot_delete_report_after_verification(client, db, citizen_headers, municipality_headers):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Lifecycle delete test",
            "description": "A verified report remains in the civic record.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    assert created.status_code == status.HTTP_201_CREATED
    report_id = created.json()["id"]

    verified = client.patch(
        f"/api/v1/reports/{report_id}/status",
        json={"status": "VERIFIED", "comment": "Lifecycle test verification."},
        headers=municipality_headers,
    )
    assert verified.status_code == status.HTTP_200_OK

    deleted = client.delete(f"/api/v1/reports/{report_id}", headers=citizen_headers)
    assert deleted.status_code == status.HTTP_409_CONFLICT
    assert db.query(Report).filter(Report.id == report_id).count() == 1


def test_delete_report_requires_authentication(client, citizen_headers):
    created = client.post(
        "/api/v1/reports",
        json={
            "title": "Authenticated delete test",
            "description": "Deletion requires a session.",
            "latitude": 18.5204,
            "longitude": 73.8567,
        },
        headers=citizen_headers,
    )
    response = client.delete(f"/api/v1/reports/{created.json()['id']}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_upvotes_toggle_and_uniqueness(client, citizen_headers, admin_headers):
    create_res = client.post(
        "/api/v1/reports",
        json={
            "title": "Upvote test report",
            "description": "Report for testing upvotes",
            "latitude": 18.5200,
            "longitude": 73.8500,
        },
        headers=citizen_headers,
    )
    report_id = create_res.json()["id"]

    # Citizen upvotes
    u1 = client.post(f"/api/v1/reports/{report_id}/upvote", headers=citizen_headers)
    assert u1.status_code == status.HTTP_200_OK
    assert u1.json()["has_upvoted"] is True
    assert u1.json()["total_upvotes"] == 1

    # Citizen upvotes again -> toggles off
    u2 = client.post(f"/api/v1/reports/{report_id}/upvote", headers=citizen_headers)
    assert u2.status_code == status.HTTP_200_OK
    assert u2.json()["has_upvoted"] is False
    assert u2.json()["total_upvotes"] == 0

    # Admin upvotes
    u3 = client.post(f"/api/v1/reports/{report_id}/upvote", headers=admin_headers)
    assert u3.status_code == status.HTTP_200_OK
    assert u3.json()["total_upvotes"] == 1


def test_municipality_stats(client, municipality_headers):
    res = client.get("/api/v1/municipality/stats", headers=municipality_headers)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()
    assert "total_reports" in data
    assert "by_category" in data
