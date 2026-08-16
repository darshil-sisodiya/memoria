"""Conversation API schemas used by the Phase 2 endpoints."""

from datetime import datetime

from pydantic import Field

from backend.app.schemas.common import ReadSchema


class ConversationCreate(ReadSchema):
    person_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)


class ConversationMessageRead(ReadSchema):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime


class ConversationRead(ReadSchema):
    id: int
    person_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[ConversationMessageRead] = Field(default_factory=list)
