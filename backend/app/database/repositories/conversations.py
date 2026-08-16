"""Conversation repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.database.models import Conversation


class ConversationRepository:
    """Persistence operations for conversations."""

    def list(self, session: Session, person_id: int | None = None) -> list[Conversation]:
        statement = select(Conversation).options(selectinload(Conversation.messages)).order_by(Conversation.id)
        if person_id is not None:
            statement = statement.where(Conversation.person_id == person_id)
        return list(session.scalars(statement))

    def get(self, session: Session, conversation_id: int) -> Conversation | None:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id)
        )
        return session.scalar(statement)

    def create(self, session: Session, person_id: int, title: str) -> Conversation:
        conversation = Conversation(person_id=person_id, title=title)
        session.add(conversation)
        session.commit()
        session.refresh(conversation)
        return conversation

