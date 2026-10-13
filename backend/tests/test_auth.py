from fastapi import status


def test_register_success(client):
    response = client.post(
        "/api/v1/register",
        json={
            "email": "newcitizen@civic.org",
            "password": "SecurePassword123!",
            "full_name": "New Citizen",
            "role": "citizen",
        },

    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "newcitizen@civic.org"
    assert data["role"] == "citizen"
    assert "id" in data


def test_register_duplicate_email(client, citizen_user):
    response = client.post(
        "/api/v1/register",
        json={
            "email": citizen_user.email,
            "password": "AnotherPassword123!",
            "full_name": "Duplicate User",
            "role": "citizen",
        },
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_public_registration_cannot_assign_privileged_role(client):
    response = client.post(
        "/api/v1/register",
        json={
            "email": "attempted.admin@civic.org",
            "password": "SecurePassword123!",
            "full_name": "Attempted Admin",
            "role": "admin",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_login_success(client, citizen_user):
    response = client.post(
        "/api/v1/login",
        json={
            "email": citizen_user.email,
            "password": "Password123!",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client, citizen_user):
    response = client.post(
        "/api/v1/login",
        json={
            "email": citizen_user.email,
            "password": "WrongPassword!",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_me_authenticated(client, citizen_headers, citizen_user):
    response = client.get("/api/v1/me", headers=citizen_headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == citizen_user.id
    assert data["email"] == citizen_user.email


def test_me_unauthorized(client):
    response = client.get("/api/v1/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_profile_update_only_changes_public_profile_fields(client, citizen_headers, citizen_user):
    response = client.patch(
        "/api/v1/users/me",
        headers=citizen_headers,
        json={"full_name": "Updated Citizen", "email": "updated@civic.org", "role": "admin"},
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["full_name"] == "Updated Citizen"
    assert response.json()["email"] == "updated@civic.org"
    assert response.json()["role"] == "citizen"


def test_profile_update_rejects_duplicate_email(client, citizen_headers, citizen_user, admin_user):
    response = client.patch(
        "/api/v1/users/me",
        headers=citizen_headers,
        json={"email": admin_user.email},
    )
    assert response.status_code == status.HTTP_409_CONFLICT


def test_profile_update_requires_authentication(client):
    response = client.patch("/api/v1/users/me", json={"full_name": "No Token"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_malformed_token_subject_returns_401(client):
    from app.core.security import create_access_token

    token = create_access_token({"sub": "not-an-integer"})
    response = client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_role_authorization_admin_endpoint(client, citizen_headers, admin_headers):
    # Citizen trying to access admin endpoint
    res_citizen = client.get("/api/v1/admin-test", headers=citizen_headers)
    assert res_citizen.status_code == status.HTTP_403_FORBIDDEN

    # Admin accessing admin endpoint
    res_admin = client.get("/api/v1/admin-test", headers=admin_headers)
    assert res_admin.status_code == status.HTTP_200_OK
    assert "Welcome Admin" in res_admin.json()["message"]


def test_forgot_password(client, citizen_user):
    response = client.post(
        "/api/v1/forgot-password",
        json={"email": citizen_user.email},
    )
    assert response.status_code == status.HTTP_200_OK
    assert "message" in response.json()


def test_password_reset_token_is_hashed_single_use_and_changes_password(
    client, citizen_user, monkeypatch
):
    issued_tokens = []

    async def capture_reset_email(email, token):
        issued_tokens.append(token)

    monkeypatch.setattr("app.services.user_service.send_reset_email", capture_reset_email)
    response = client.post(
        "/api/v1/forgot-password",
        json={"email": citizen_user.email},
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(issued_tokens) == 1
    assert citizen_user.reset_token != issued_tokens[0]

    reset = client.post(
        "/api/v1/reset-password",
        json={"token": issued_tokens[0], "new_password": "UpdatedPassword123!"},
    )
    assert reset.status_code == status.HTTP_200_OK
    assert client.post(
        "/api/v1/reset-password",
        json={"token": issued_tokens[0], "new_password": "AnotherPassword123!"},
    ).status_code == status.HTTP_400_BAD_REQUEST
    assert client.post(
        "/api/v1/login",
        json={"email": citizen_user.email, "password": "UpdatedPassword123!"},
    ).status_code == status.HTTP_200_OK


def test_registration_and_password_reset_reject_short_passwords(client):
    registration = client.post(
        "/api/v1/register",
        json={"email": "short-pass@test.org", "password": "short", "full_name": "Short Pass"},
    )
    reset = client.post(
        "/api/v1/reset-password",
        json={"token": "any-token", "new_password": "short"},
    )
    assert registration.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert reset.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
