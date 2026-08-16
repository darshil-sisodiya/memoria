"""Chat API endpoint for local LLM development."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.app.core.config import Settings, get_settings
from backend.app.llm.exceptions import LocalLLMError
from backend.app.llm.local_llama import LocalLlamaProvider


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.7


class ChatResponse(BaseModel):
    content: str


def get_llm_provider(settings: Settings = Depends(get_settings)) -> LocalLlamaProvider:
    if settings.llm_provider != "local":
        raise HTTPException(status_code=501, detail=f"Provider {settings.llm_provider} is not implemented")
    return LocalLlamaProvider(base_url=settings.llm_base_url, model=settings.llm_model)


@router.post("", response_model=ChatResponse)
async def generate_chat(
    request: ChatRequest,
    provider: LocalLlamaProvider = Depends(get_llm_provider),
) -> Any:
    """Send a basic generation request to the local LLM provider."""
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    try:
        content = await provider.generate(messages=messages, temperature=request.temperature)
        return ChatResponse(content=content)
    except LocalLLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
