"""Person API schemas."""

from datetime import datetime

from pydantic import Field

from backend.app.schemas.common import ReadSchema


class PersonCreate(ReadSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class PersonRead(ReadSchema):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

