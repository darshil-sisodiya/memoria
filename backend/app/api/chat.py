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
    use_memory: bool = False
    person_id: int | None = None

class ChatResponse(BaseModel):
    content: str

def get_llm_provider(settings: Settings = Depends(get_settings)) -> LocalLlamaProvider:
    if settings.llm_provider != "local":
        raise HTTPException(status_code=501, detail=f"Provider {settings.llm_provider} is not implemented")
    return LocalLlamaProvider(base_url=settings.llm_base_url, model=settings.llm_model)

from fastapi import Request
from backend.app.rag.retrieval import RetrievalService
from backend.app.rag.context_builder import ContextBuilder
import logging

logger = logging.getLogger(__name__)

def get_retrieval_service(request: Request) -> RetrievalService:
    return RetrievalService(
        embedding_provider=request.app.state.embedding_provider,
        vector_store=request.app.state.vector_store
    )

def get_context_builder() -> ContextBuilder:
    return ContextBuilder()

@router.post("", response_model=ChatResponse)
async def generate_chat(
    request: ChatRequest,
    provider: LocalLlamaProvider = Depends(get_llm_provider),
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    context_builder: ContextBuilder = Depends(get_context_builder),
    settings: Settings = Depends(get_settings)
) -> Any:
    """Send a basic generation request to the local LLM provider, optionally using memory retrieval."""
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages array cannot be empty")

    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

    if request.use_memory:
        # Get the latest user query for retrieval
        user_queries = [msg.content for msg in request.messages if msg.role == "user"]
        if user_queries:
            latest_query = user_queries[-1]
            try:
                retrieved_chunks = await retrieval_service.retrieve_history(
                    query=latest_query,
                    top_k=settings.rag_top_k,
                    person_id=request.person_id
                )
                if retrieved_chunks:
                    # Construct system prompt
                    system_prompt = context_builder.build_system_prompt(retrieved_chunks)
                    
                    # Prepend system prompt to messages
                    # If there's already a system prompt, we replace or prepend. We'll just prepend it.
                    if messages[0]["role"] == "system":
                        # Replace the first system message's content
                        messages[0]["content"] = system_prompt
                    else:
                        messages.insert(0, {"role": "system", "content": system_prompt})
            except Exception as e:
                logger.error(f"Failed to retrieve memory: {e}")
                # We do not fail the whole request, we just proceed without memory

    try:
        content = await provider.generate(messages=messages, temperature=request.temperature)
        return ChatResponse(content=content)
    except LocalLLMError as e:
        raise HTTPException(status_code=503, detail=str(e))
