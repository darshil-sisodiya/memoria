"""Memory repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models import Memory


class MemoryRepository:
    """Persistence operations for memories."""

    def list(self, session: Session, person_id: int | None = None) -> list[Memory]:
        statement = select(Memory).order_by(Memory.id)
        if person_id is not None:
            statement = statement.where(Memory.person_id == person_id)
        return list(session.scalars(statement))

    def get(self, session: Session, memory_id: int) -> Memory | None:
        return session.get(Memory, memory_id)

    def create(self, session: Session, memory: Memory) -> Memory:
        session.add(memory)
        session.commit()
        session.refresh(memory)
        return memory

    def delete(self, session: Session, memory: Memory) -> None:
        session.delete(memory)
        session.commit()

