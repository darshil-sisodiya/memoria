"""LLM Provider interfaces."""

from typing import Any, Protocol


class LLMProvider(Protocol):
    """Base interface for all LLM providers in Memoria."""

    async def health_check(self) -> bool:
        """Check if the LLM provider is available."""
        ...

    async def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Generate a response from the LLM based on conversation history."""
        ...
