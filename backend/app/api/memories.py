"""Memory API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db, get_embedding_provider, get_vector_store
from backend.app.database.repositories.people import PersonRepository
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorStore
from backend.app.schemas.memory import MemoryCreate, MemoryRead
from backend.app.services.memory_service import MemoryService


router = APIRouter(prefix="/api/memories", tags=["memories"])


@router.get("", response_model=list[MemoryRead])
def list_memories(
    person_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[MemoryRead]:
    return MemoryService().list_memories(db, person_id)


@router.post("", response_model=MemoryRead, status_code=status.HTTP_201_CREATED)
async def create_memory(
    payload: MemoryCreate,
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> MemoryRead:
    if PersonRepository().get(db, payload.person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return await MemoryService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    ).create_memory(
        db,
        person_id=payload.person_id,
        title=payload.title,
        content=payload.content,
        timestamp=payload.timestamp,
        source=payload.source,
        source_id=payload.source_id,
        importance=payload.importance,
    )


@router.get("/{memory_id}", response_model=MemoryRead)
def get_memory(memory_id: int, db: Session = Depends(get_db)) -> MemoryRead:
    memory = MemoryService().get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    return memory


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: int,
    db: Session = Depends(get_db),
    vector_store: VectorStore = Depends(get_vector_store),
) -> Response:
    service = MemoryService()
    memory = service.get_memory(db, memory_id)
    if memory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")
    await MemoryService(vector_store=vector_store).delete_memory(db, memory)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
