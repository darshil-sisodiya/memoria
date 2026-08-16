"""People API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_db
from backend.app.schemas.people import PersonCreate, PersonRead
from backend.app.services.person_service import PersonService


router = APIRouter(prefix="/api/people", tags=["people"])


@router.get("", response_model=list[PersonRead])
def list_people(db: Session = Depends(get_db)) -> list[PersonRead]:
    return PersonService().list_people(db)


@router.post("", response_model=PersonRead, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)) -> PersonRead:
    return PersonService().create_person(db, payload.name, payload.description)


@router.get("/{person_id}", response_model=PersonRead)
def get_person(person_id: int, db: Session = Depends(get_db)) -> PersonRead:
    person = PersonService().get_person(db, person_id)
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person

