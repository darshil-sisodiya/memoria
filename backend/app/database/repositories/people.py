"""Person repository."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.models import Person


class PersonRepository:
    """Persistence operations for people."""

    def list(self, session: Session) -> list[Person]:
        return list(session.scalars(select(Person).order_by(Person.id)))

    def get(self, session: Session, person_id: int) -> Person | None:
        return session.get(Person, person_id)

    def create(self, session: Session, name: str, description: str | None) -> Person:
        person = Person(name=name, description=description)
        session.add(person)
        session.commit()
        session.refresh(person)
        return person

