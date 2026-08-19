"""Unit tests for the RAG pipeline."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.database.models import Message, Person
from backend.app.rag.chunking import ConversationChunker
from backend.app.rag.context_builder import ContextBuilder
from backend.app.rag.indexer import IndexerService
from backend.app.rag.retrieval import RetrievalService
from backend.app.rag.vector_store import VectorDocument, VectorSearchResult
from backend.app.rag.embeddings import MockEmbeddingProvider
from backend.app.api.chat import get_retrieval_service, get_context_builder, get_llm_provider
from fastapi.testclient import TestClient

# 1. Chunking & Stable IDs Tests
def test_conversation_chunker_stable_ids_and_boundaries():
    chunker = ConversationChunker(gap_minutes=30, max_characters=100)
    
    dt1 = datetime(2025, 1, 1, 10, 0, 0)
    messages = [
        Message(id=1, person_id=1, sender="Darshil", content="Hello!", timestamp=dt1),
        Message(id=2, person_id=1, sender="You", content="Hey!", timestamp=dt1 + timedelta(minutes=5)),
        # Should start new chunk because of gap
        Message(id=3, person_id=1, sender="Darshil", content="Later...", timestamp=dt1 + timedelta(minutes=36)),
        # Should start new chunk because of length
        Message(id=4, person_id=1, sender="Darshil", content="A" * 150, timestamp=dt1 + timedelta(minutes=37)),
        # Should be skipped because media
        Message(id=5, person_id=1, sender="Darshil", content="<Media omitted>", timestamp=dt1 + timedelta(minutes=38)),
        # Should be skipped because system
        Message(id=6, person_id=1, sender="", content="System notice", timestamp=dt1 + timedelta(minutes=39)),
    ]
    
    chunks = chunker.create_chunks(messages)
    
    # Expected chunks:
    # Chunk 1: messages 1, 2
    # Chunk 2: message 3
    # Chunk 3: message 4
    # messages 5, 6 skipped
    assert len(chunks) == 3
    
    # Stable ID test
    chunk_1_id = chunks[0].id
    assert chunk_1_id.startswith("chunk:")
    
    # Re-running produces identical chunks/IDs
    chunks_again = chunker.create_chunks(messages[:2])
    assert chunks_again[0].id == chunk_1_id
    
    # Metadata preservation
    assert chunks[0].metadata["message_count"] == 2
    assert "Darshil" in chunks[0].metadata["participants"]
    assert "You" in chunks[0].metadata["participants"]
    assert chunks[0].metadata["first_message_id"] == 1
    assert chunks[0].metadata["last_message_id"] == 2


# 2. Indexing Tests
@pytest.mark.anyio
async def test_indexer_duplicate_prevention_and_empty_db():
    mock_vector_store = AsyncMock()
    mock_embedding_provider = AsyncMock()
    
    chunker = ConversationChunker()
    indexer = IndexerService(mock_embedding_provider, mock_vector_store, chunker)
    
    mock_session = MagicMock()
    mock_session.execute.return_value.scalars.return_value.all.return_value = []
    
    # Empty SQLite
    stats = await indexer.index_person_messages(mock_session, 1)
    assert stats["chunks_processed"] == 0
    
    # Non-empty SQLite
    messages = [
        Message(id=1, person_id=1, sender="Darshil", content="Hi", timestamp=datetime.utcnow())
    ]
    mock_session.execute.return_value.scalars.return_value.all.return_value = messages
    
    # Setup vector store to say this chunk already exists
    # Find what ID the chunker will generate
    generated_chunks = chunker.create_chunks(messages)
    chunk_id = generated_chunks[0].id
    mock_vector_store.get_existing_ids.return_value = {chunk_id}
    
    stats2 = await indexer.index_person_messages(mock_session, 1)
    assert stats2["chunks_processed"] == 1
    assert stats2["chunks_skipped"] == 1
    assert stats2["chunks_indexed"] == 0
    
    # Setup vector store to say it doesn't exist
    mock_vector_store.get_existing_ids.return_value = set()
    mock_embedding_provider.embed_batch.return_value = [[0.1, 0.2]]
    
    stats3 = await indexer.index_person_messages(mock_session, 1)
    assert stats3["chunks_indexed"] == 1
    mock_vector_store.add_documents.assert_called_once()


# 3. Retrieval & Top-K Tests
@pytest.mark.anyio
async def test_retrieval_service_filters_and_top_k():
    mock_vector_store = AsyncMock()
    mock_embedding_provider = AsyncMock()
    
    retrieval_service = RetrievalService(mock_embedding_provider, mock_vector_store)
    mock_embedding_provider.embed_text.return_value = [0.5, 0.5]
    mock_vector_store.search.return_value = [
        VectorSearchResult(id="1", content="Result 1", score=0.9, metadata={}),
        VectorSearchResult(id="2", content="Result 2", score=0.8, metadata={})
    ]
    
    # Test 1: Both source_type and person_id (Compound Filter)
    results = await retrieval_service.retrieve_history("test query", top_k=2, person_id=1)
    assert len(results) == 2
    mock_vector_store.search.assert_called_with(
        collection="messages",
        query_embedding=[0.5, 0.5],
        top_k=2,
        where={"$and": [{"source_type": "conversation_chunk"}, {"person_id": 1}]}
    )
    
    # Test 2: Only source_type (person_id is None)
    mock_vector_store.search.reset_mock()
    results_no_person = await retrieval_service.retrieve_history("test query", top_k=5, person_id=None)
    assert len(results_no_person) == 2
    mock_vector_store.search.assert_called_with(
        collection="messages",
        query_embedding=[0.5, 0.5],
        top_k=5,
        where={"source_type": "conversation_chunk"}
    )
    
    # Test 3: Empty retrieval result
    mock_vector_store.search.return_value = []
    results_empty = await retrieval_service.retrieve_history("test query")
    assert results_empty == []

@pytest.mark.anyio
async def test_retrieval_failure_graceful_degradation():
    mock_vector_store = AsyncMock()
    mock_embedding_provider = AsyncMock()
    mock_embedding_provider.embed_text.side_effect = Exception("Model unavailable")
    
    retrieval_service = RetrievalService(mock_embedding_provider, mock_vector_store)
    results = await retrieval_service.retrieve_history("test query")
    assert results == []  # Graceful degradation


# 4. Context Builder Tests
def test_context_builder_formatting():
    builder = ContextBuilder(system_instruction="System instructions.")
    
    history = [
        VectorSearchResult(
            id="1", 
            content="Darshil: Hey", 
            score=1.0, 
            metadata={"start_timestamp": "2025-01-01T10:00:00", "end_timestamp": "2025-01-01T10:01:00"}
        )
    ]
    
    prompt = builder.build_system_prompt(history)
    assert "System instructions." in prompt
    assert "RELEVANT CONVERSATION HISTORY:" in prompt
    assert "Darshil: Hey" in prompt
    assert "2025-01-01T10:00:00" in prompt
    
    # Test empty history
    empty_prompt = builder.build_system_prompt([])
    assert empty_prompt == "System instructions."


# 5. API Tests
@pytest.fixture
def mock_retrieval_service():
    service = AsyncMock()
    service.retrieve_history.return_value = [
        VectorSearchResult(id="1", content="Darshil: Memory content", score=0.9, metadata={})
    ]
    return service

@pytest.fixture
def test_app():
    from backend.app.core.config import Settings
    from backend.app.main import create_app
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
def test_client_with_rag(test_app, mock_retrieval_service):
    from backend.app.core.config import get_settings, Settings
    settings = Settings(llm_provider="local")
    
    # Override dependencies
    test_app.dependency_overrides[get_settings] = lambda: settings
    test_app.dependency_overrides[get_retrieval_service] = lambda: mock_retrieval_service
    
    # Mock LLM provider
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "LLM response"
    test_app.dependency_overrides[get_llm_provider] = lambda: mock_llm
    
    return TestClient(test_app), mock_llm, mock_retrieval_service

def test_api_chat_use_memory_false(test_client_with_rag):
    client, mock_llm, mock_retrieval = test_client_with_rag
    
    response = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "Hello"}],
        "use_memory": False
    })
    
    assert response.status_code == 200
    mock_retrieval.retrieve_history.assert_not_called()
    mock_llm.generate.assert_called_once()
    args, kwargs = mock_llm.generate.call_args
    assert len(kwargs["messages"]) == 1
    assert kwargs["messages"][0]["content"] == "Hello"

def test_api_chat_use_memory_true(test_client_with_rag):
    client, mock_llm, mock_retrieval = test_client_with_rag
    
    response = client.post("/api/chat", json={
        "messages": [{"role": "user", "content": "What did we discuss?"}],
        "use_memory": True
    })
    
    assert response.status_code == 200
    mock_retrieval.retrieve_history.assert_called_once_with(
        query="What did we discuss?",
        top_k=5,
        person_id=None
    )
    
    mock_llm.generate.assert_called_once()
    args, kwargs = mock_llm.generate.call_args
    # System prompt should be prepended
    assert len(kwargs["messages"]) == 2
    assert kwargs["messages"][0]["role"] == "system"
    assert "RELEVANT CONVERSATION HISTORY" in kwargs["messages"][0]["content"]
    assert "Darshil: Memory content" in kwargs["messages"][0]["content"]
