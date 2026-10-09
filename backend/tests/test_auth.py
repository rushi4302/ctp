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
