"""Import API schemas."""

from uuid import UUID

from backend.app.schemas.common import ReadSchema


class ImportSummary(ReadSchema):
    import_id: UUID
    status: str
    messages_imported: int
    messages_skipped: int
    errors: int

