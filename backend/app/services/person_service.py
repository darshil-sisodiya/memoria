"""Person application service."""

from sqlalchemy.orm import Session

from backend.app.database.models import Person
from backend.app.database.repositories.people import PersonRepository


class PersonService:
    """Coordinate person operations without exposing persistence details to routes."""

    def __init__(self, repository: PersonRepository | None = None) -> None:
        self.repository = repository or PersonRepository()

    def list_people(self, session: Session) -> list[Person]:
        return self.repository.list(session)

    def get_person(self, session: Session, person_id: int) -> Person | None:
        return self.repository.get(session, person_id)

    def create_person(self, session: Session, name: str, description: str | None) -> Person:
        return self.repository.create(session, name, description)

