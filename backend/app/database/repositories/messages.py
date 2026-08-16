"""Message repository."""

from collections.abc import Iterable

from sqlalchemy.orm import Session

from backend.app.database.models import Message


class MessageRepository:
    """Persistence operations for imported and manually-created messages."""

    def add_many(
        self,
        session: Session,
        messages: Iterable[Message],
        *,
        commit: bool = True,
    ) -> list[Message]:
        saved_messages = list(messages)
        session.add_all(saved_messages)
        if commit:
            session.commit()
        else:
            session.flush()
        return saved_messages
