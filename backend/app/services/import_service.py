"""WhatsApp import application service."""

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.database.models import Message
from backend.app.database.repositories.messages import MessageRepository
from backend.app.database.repositories.people import PersonRepository
from backend.app.importers.whatsapp import WhatsAppParser
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorDocument, VectorStore
from backend.app.schemas.imports import ImportSummary


class ImportService:
    """Parse local exports and persist their messages in one transaction."""

    def __init__(
        self,
        parser: WhatsAppParser | None = None,
        people: PersonRepository | None = None,
        messages: MessageRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self.parser = parser or WhatsAppParser()
        self.people = people or PersonRepository()
        self.messages = messages or MessageRepository()
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    async def import_whatsapp(
        self,
        session: Session,
        *,
        person_id: int,
        filename: str,
        text: str,
    ) -> ImportSummary:
        if self.people.get(session, person_id) is None:
            raise ValueError(f"Person {person_id} was not found")

        parsed = self.parser.parse(text)
        messages = [
            Message(
                person_id=person_id,
                sender=item.sender,
                content=item.content,
                timestamp=item.timestamp,
                source="whatsapp",
                source_id=f"{filename}:{item.line_number}",
            )
            for item in parsed.messages
        ]
        saved_messages = self.messages.add_many(session, messages, commit=False)
        vector_ids = [f"message:{message.id}" for message in saved_messages]
        try:
            if saved_messages:
                if self.embedding_provider is None or self.vector_store is None:
                    raise RuntimeError("Embedding and vector-store providers are required for imports")
                embeddings = await self.embedding_provider.embed_batch(
                    [f"{message.sender}: {message.content}" for message in saved_messages]
                )
                await self.vector_store.add_documents(
                    "messages",
                    [
                        VectorDocument(
                            id=f"message:{message.id}",
                            content=f"{message.sender}: {message.content}",
                            metadata={
                                "source_type": "message",
                                "source_id": message.id,
                                "person_id": message.person_id,
                                "timestamp": message.timestamp.isoformat() if message.timestamp else None,
                            },
                        )
                        for message in saved_messages
                    ],
                    embeddings,
                )
            session.commit()
        except Exception:
            session.rollback()
            if vector_ids and self.vector_store is not None:
                await self.vector_store.delete("messages", vector_ids)
            raise

        import_id: UUID = uuid4()
        return ImportSummary(
            import_id=import_id,
            status="completed",
            messages_imported=len(messages),
            messages_skipped=parsed.skipped_lines,
            errors=0,
        )
