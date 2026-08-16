"""Local import API routes."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db, get_embedding_provider, get_vector_store
from backend.app.importers.whatsapp import decode_whatsapp_bytes
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorStore
from backend.app.schemas.imports import ImportSummary
from backend.app.services.import_service import ImportService


router = APIRouter(prefix="/api/import", tags=["imports"])


@router.post("/whatsapp", response_model=ImportSummary)
async def import_whatsapp(
    person_id: int = Form(..., gt=0),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
    vector_store: VectorStore = Depends(get_vector_store),
) -> ImportSummary:
    """Import a local WhatsApp `.txt` export for an existing person."""

    filename = file.filename or "whatsapp.txt"
    if not filename.lower().endswith(".txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .txt WhatsApp exports are supported",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty")

    try:
        text = decode_whatsapp_bytes(payload)
    except UnicodeDecodeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported text encoding") from error

    try:
        return await ImportService(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
        ).import_whatsapp(
            db,
            person_id=person_id,
            filename=filename,
            text=text,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
