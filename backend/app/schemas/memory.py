"""Memory API schemas."""

from datetime import datetime

from pydantic import Field

from backend.app.schemas.common import ReadSchema


class MemoryCreate(ReadSchema):
    person_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    timestamp: datetime | None = None
    source: str = Field(default="manual", min_length=1, max_length=50)
    source_id: str | None = Field(default=None, max_length=255)
    importance: int = 0


class MemoryRead(ReadSchema):
    id: int
    person_id: int
    title: str
    content: str
    timestamp: datetime | None
    source: str
    source_id: str | None
    importance: int
    created_at: datetime
    updated_at: datetime

