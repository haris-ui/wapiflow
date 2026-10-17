import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test successful user registration."""
    payload = {
        "email": "fresh_user@example.com",
        "password": "SecurePassword123!",
        "full_name": "Fresh User",
        "phone_number": "+1234567890",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["email"] == "fresh_user@example.com"
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test duplicate registration returns 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "full_name": "Duplicate User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    data = res2.json()
    assert data["error"] == "HTTP_ERROR"
    assert "already exists" in data["message"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Test login with registered user."""
    reg_payload = {
        "email": "login_test@example.com",
        "password": "Password123!",
        "full_name": "Login User",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "login_test@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["email"] == "login_test@example.com"


@pytest.mark.asyncio
async def test_get_current_user_profile(client: AsyncClient, create_user):
    """Test GET /auth/me returns profile for authenticated user."""
    user_id, headers = await create_user("profile_check@example.com", "Profile User")

    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["email"] == "profile_check@example.com"
    assert data["full_name"] == "Profile User"


@pytest.mark.asyncio
async def test_update_current_user_profile(client: AsyncClient, create_user):
    """Test PATCH /auth/me updates current user profile."""
    user_id, headers = await create_user("update_me@example.com", "Initial Name")

    update_payload = {
        "full_name": "Updated Name",
        "phone_number": "+9876543210",
    }
    response = await client.patch("/api/v1/auth/me", json=update_payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"
    assert data["phone_number"] == "+9876543210"
