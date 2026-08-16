"""Conversation API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.database.repositories.people import PersonRepository
from backend.app.schemas.chat import ConversationCreate, ConversationRead
from backend.app.services.conversation_service import ConversationService


router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationRead])
def list_conversations(
    person_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
) -> list[ConversationRead]:
    return ConversationService().list_conversations(db, person_id)


@router.post("", response_model=ConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)) -> ConversationRead:
    if PersonRepository().get(db, payload.person_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return ConversationService().create_conversation(db, payload.person_id, payload.title)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)) -> ConversationRead:
    conversation = ConversationService().get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation

