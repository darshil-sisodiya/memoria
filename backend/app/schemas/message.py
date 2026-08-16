"""Message schemas used by importer tests and future APIs."""

from datetime import datetime

from backend.app.schemas.common import ReadSchema


class MessageRead(ReadSchema):
    id: int
    person_id: int
    sender: str
    content: str
    timestamp: datetime | None
    source: str
    source_id: str | None
    created_at: datetime

