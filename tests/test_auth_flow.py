import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from app.main import app
from app.dependencies import get_supabase, get_current_user
from app.config import settings

client = TestClient(app)

@pytest.fixture
def mock_supabase():
    with patch("app.routers.auth.get_supabase") as mock:
        yield mock

def test_signup_requires_confirmation(mock_supabase):
    mock_auth = MagicMock()
    # Mock response with no session (requires confirmation)
    mock_auth.sign_up.return_value = MagicMock(session=None)
    mock_supabase.return_value.auth = mock_auth
    
    response = client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    
    assert response.status_code == 201
    assert response.json()["requires_confirmation"] is True

def test_signup_immediate_session(mock_supabase):
    mock_auth = MagicMock()
    # Mock response with session
    mock_session = MagicMock()
    mock_session.access_token = "fake-token"
    mock_session.token_type = "bearer"
    mock_auth.sign_up.return_value = MagicMock(session=mock_session)
    mock_supabase.return_value.auth = mock_auth
    
    response = client.post("/auth/signup", json={"email": "test@example.com", "password": "password123"})
    
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-token"

def test_login_success(mock_supabase):
    mock_auth = MagicMock()
    mock_session = MagicMock()
    mock_session.access_token = "fake-token"
    mock_session.token_type = "bearer"
    mock_auth.sign_in_with_password.return_value = MagicMock(session=mock_session)
    mock_supabase.return_value.auth = mock_auth
    
    response = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    
    assert response.status_code == 200
    assert response.json()["access_token"] == "fake-token"

def test_get_me_success():
    from app.models import UserProfile
    mock_user = UserProfile(id="user-123", email="test@example.com", role="user")
    
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = client.get("/auth/me", headers={"Authorization": "Bearer some-token"})
        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"
    finally:
        app.dependency_overrides = {}
