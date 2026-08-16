"""Local llama.cpp inference provider using OpenAI-compatible HTTP API."""

from typing import Any

import httpx

from backend.app.llm.exceptions import LocalLLMError
from backend.app.llm.interfaces import LLMProvider


class LocalLlamaProvider(LLMProvider):
    """Provider for a locally running llama-server."""

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def health_check(self) -> bool:
        """Verify the local LLM server is reachable via the models endpoint."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                return True
        except httpx.RequestError:
            return False
        except httpx.HTTPStatusError:
            return False

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate text using the local llama-server completions endpoint."""
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        
        try:
            async with httpx.AsyncClient(timeout=kwargs.get("timeout", 60.0)) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                if not data or "choices" not in data or not data["choices"]:
                    raise LocalLLMError("Empty or malformed response from local LLM server.")
                
                message = data["choices"][0].get("message", {})
                content = message.get("content")
                if content is None:
                    raise LocalLLMError("Empty or malformed response from local LLM server.")
                    
                return content
                
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise LocalLLMError(f"Local LLM server is unavailable at {self.base_url}") from e
        except httpx.HTTPStatusError as e:
            raise LocalLLMError(f"Local LLM server returned HTTP error {e.response.status_code}") from e
        except ValueError as e:
            # JSON decode error
            raise LocalLLMError("Empty or malformed response from local LLM server.") from e
