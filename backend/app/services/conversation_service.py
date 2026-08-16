"""Conversation application service."""

from sqlalchemy.orm import Session

from backend.app.database.models import Conversation
from backend.app.database.repositories.conversations import ConversationRepository


class ConversationService:
    """Coordinate conversation persistence."""

    def __init__(self, repository: ConversationRepository | None = None) -> None:
        self.repository = repository or ConversationRepository()

    def list_conversations(self, session: Session, person_id: int | None = None) -> list[Conversation]:
        return self.repository.list(session, person_id)

    def get_conversation(self, session: Session, conversation_id: int) -> Conversation | None:
        return self.repository.get(session, conversation_id)

    def create_conversation(self, session: Session, person_id: int, title: str) -> Conversation:
        return self.repository.create(session, person_id, title)

