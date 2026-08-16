"""Unit tests for the local llama-server provider."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from backend.app.llm.exceptions import LocalLLMError
from backend.app.llm.local_llama import LocalLlamaProvider


@pytest.fixture
def provider() -> LocalLlamaProvider:
    return LocalLlamaProvider(base_url="http://127.0.0.1:8080/v1", model="test-model")


@pytest.mark.anyio
async def test_health_check_success(provider: LocalLlamaProvider) -> None:
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        is_healthy = await provider.health_check()
        
        assert is_healthy is True
        mock_get.assert_called_once_with("http://127.0.0.1:8080/v1/models")


@pytest.mark.anyio
async def test_health_check_failure(provider: LocalLlamaProvider) -> None:
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        is_healthy = await provider.health_check()
        
        assert is_healthy is False


@pytest.mark.anyio
async def test_successful_generation(provider: LocalLlamaProvider) -> None:
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value={
            "choices": [
                {"message": {"content": "Hi there!"}}
            ]
        })
        mock_post.return_value = mock_response

        response = await provider.generate(messages=messages, temperature=0.5)
        
        assert response == "Hi there!"
        mock_post.assert_called_once_with(
            "http://127.0.0.1:8080/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": messages,
                "temperature": 0.5,
            }
        )


@pytest.mark.anyio
async def test_respects_configured_port_and_model() -> None:
    custom_provider = LocalLlamaProvider(base_url="http://127.0.0.1:9000/v1", model="custom-gguf")
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.json = Mock(return_value={"choices": [{"message": {"content": "Ok"}}]})
        mock_post.return_value = mock_response

        await custom_provider.generate(messages=messages)
        
        mock_post.assert_called_once_with(
            "http://127.0.0.1:9000/v1/chat/completions",
            json={"model": "custom-gguf", "messages": messages}
        )


@pytest.mark.anyio
async def test_connection_failure_raises_local_error(provider: LocalLlamaProvider) -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(LocalLLMError, match="Local LLM server is unavailable at http://127.0.0.1:8080/v1"):
            await provider.generate(messages=[])


@pytest.mark.anyio
async def test_timeout_raises_local_error(provider: LocalLlamaProvider) -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Timeout")

        with pytest.raises(LocalLLMError, match="Local LLM server is unavailable"):
            await provider.generate(messages=[])


@pytest.mark.anyio
async def test_http_error_status_raises_local_error(provider: LocalLlamaProvider) -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
            message="Internal Server Error",
            request=AsyncMock(),
            response=mock_response
        ))
        mock_post.return_value = mock_response

        with pytest.raises(LocalLLMError, match="Local LLM server returned HTTP error 500"):
            await provider.generate(messages=[])


@pytest.mark.anyio
@pytest.mark.parametrize("invalid_response", [
    {},
    {"choices": []},
    {"choices": [{}]},
    {"choices": [{"message": {}}]},
    {"choices": [{"message": {"content": None}}]},
])
async def test_malformed_empty_responses(provider: LocalLlamaProvider, invalid_response: dict) -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_response.json = Mock(return_value=invalid_response)
        mock_post.return_value = mock_response

        with pytest.raises(LocalLLMError, match="Empty or malformed response"):
            await provider.generate(messages=[])
