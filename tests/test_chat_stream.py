import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock
from app.main import app
from app.models import UserProfile
from app.dependencies import get_current_user

client = TestClient(app)

@pytest.fixture
def mock_user():
    return UserProfile(id="user-123", email="test@example.com", role="user", token="fake-jwt")

def test_chat_query_streaming(mock_user):
    # Mock research_service.run_research_stream
    async def mock_stream(*args, **kwargs):
        # First chunk: Metadata
        yield json.dumps({
            "sources": [{"title": "Case A", "url": "http://a.com", "snippet": "...", "similarity": 0.9}],
            "conversation_id": "conv-123",
            "intent": "RESEARCH"
        })
        # Subsequent chunks: Tokens
        yield "Hello"
        yield " world"

    with patch("app.routers.chat.research_service.run_research_stream", side_effect=mock_stream):
        app.dependency_overrides[get_current_user] = lambda: mock_user
        try:
            # Use TestClient with stream=True or just iterate over response
            response = client.post(
                "/chat/query", 
                json={"query": "test query", "scope": "HYBRID"},
                headers={"Authorization": "Bearer fake-jwt"}
            )
            
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
            
            lines = [line for line in response.iter_lines() if line]
            
            # Check metadata line
            assert "data: {\"sources\":" in lines[0]
            assert "\"conversation_id\": \"conv-123\"" in lines[0]
            
            # Check token lines
            assert "data: {\"token\": \"Hello\"}" in lines[1]
            assert "data: {\"token\": \" world\"}" in lines[2]
            
            # Check done line
            assert "data: [DONE]" in lines[3]
        finally:
            app.dependency_overrides = {}
