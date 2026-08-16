"""Tests for the chat API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.llm.exceptions import LocalLLMError
from backend.app.main import create_app


@pytest.fixture
def test_app():
    settings = Settings(
        llm_provider="local",
        llm_base_url="http://127.0.0.1:8080/v1",
        llm_model="test-model"
    )
    app = create_app(settings)
    from backend.app.core.config import get_settings
    app.dependency_overrides[get_settings] = lambda: settings
    return app


@pytest.fixture
def client(test_app):
    return TestClient(test_app)


def test_chat_success(client: TestClient) -> None:
    with patch("backend.app.llm.local_llama.LocalLlamaProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = "Response from LLM"
        
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "temperature": 0.5
            }
        )
        
        assert response.status_code == 200
        assert response.json() == {"content": "Response from LLM"}
        
        mock_generate.assert_called_once_with(
            messages=[{"role": "user", "content": "Hello"}],
            temperature=0.5
        )


def test_chat_local_llm_error_returns_503(client: TestClient) -> None:
    with patch("backend.app.llm.local_llama.LocalLlamaProvider.generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.side_effect = LocalLLMError("Local LLM server is unavailable")
        
        response = client.post(
            "/api/chat",
            json={
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        
        assert response.status_code == 503
        assert response.json() == {"detail": "Local LLM server is unavailable"}


def test_chat_invalid_provider_returns_501() -> None:
    settings = Settings(llm_provider="invalid")
    app = create_app(settings)
    from backend.app.core.config import get_settings
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    
    response = client.post(
        "/api/chat",
        json={
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    
    assert response.status_code == 501
    assert "Provider invalid is not implemented" in response.json()["detail"]
