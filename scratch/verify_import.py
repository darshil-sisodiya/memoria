import asyncio
from datetime import datetime
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import os
import sys

# Setup path so backend is importable
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.database import Base
from backend.app.database.models import Person, Message
from backend.app.importers.whatsapp import WhatsAppParser
from backend.app.services.import_service import ImportService
from backend.app.rag.embeddings import EmbeddingProvider
from backend.app.rag.vector_store import VectorStore

class DummyEmbeddingProvider(EmbeddingProvider):
    async def embed_text(self, text):
        return [0.0] * 1536
    async def embed(self, text):
        return [0.0] * 1536
    async def embed_batch(self, texts):
        return [[0.0] * 1536 for _ in texts]
    async def embed_batch(self, texts):
        return [[0.0] * 1536 for _ in texts]

class DummyVectorStore(VectorStore):
    async def add_documents(self, collection_name, documents, embeddings):
        pass
    async def search(self, collection_name, query_embedding, limit=5, filter_metadata=None):
        return []
    async def delete(self, collection_name, document_ids):
        pass

async def main():
    chat_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "tests", "data", "whatsapp", "chat.txt"))
    
    with open(chat_file, "r", encoding="utf-8") as f:
        text = f.read()

    total_input_lines = len(text.splitlines())
    
    parser = WhatsAppParser()
    parsed = parser.parse(text)
    messages = parsed.messages
    
    parsed_messages = len(messages)
    system_messages = sum(1 for m in messages if m.is_system)
    media_messages = sum(1 for m in messages if m.is_media)
    multiline_messages = sum(1 for m in messages if "\n" in m.content)
    malformed_records = sum(1 for m in messages if m.timestamp is None and m.is_system and not m.is_media)
    
    unique_speakers = len({m.sender for m in messages if m.sender})
    
    timestamps = [m.timestamp for m in messages if m.timestamp]
    earliest_timestamp = min(timestamps) if timestamps else None
    latest_timestamp = max(timestamps) if timestamps else None

    print(f"Total input lines: {total_input_lines}")
    print(f"Parsed messages: {parsed_messages}")
    print(f"System messages: {system_messages}")
    print(f"Media messages: {media_messages}")
    print(f"Multiline messages: {multiline_messages}")
    print(f"Malformed/Unrecognized: {malformed_records}")
    print(f"Unique speakers: {unique_speakers}")
    print(f"Earliest timestamp: {earliest_timestamp}")
    print(f"Latest timestamp: {latest_timestamp}")
    
    # DB test
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    
    with Session(engine) as session:
        person = Person(name="Test Subject")
        session.add(person)
        session.commit()
        session.refresh(person)
        
        svc = ImportService(embedding_provider=DummyEmbeddingProvider(), vector_store=DummyVectorStore())
        summary = await svc.import_whatsapp(session, person_id=person.id, filename="chat.txt", text=text)
        
        print(f"Import Summary: imported={summary.messages_imported}, skipped={summary.messages_skipped}")
        
        total_rows = session.execute(select(Message)).scalars().all()
        
        db_total_messages = len(total_rows)
        db_system_messages = sum(1 for m in total_rows if not m.sender)
        db_media_messages = sum(1 for m in total_rows if "<Media omitted>" in m.content or "image omitted" in m.content or "[Call]" in m.content or m.content in ("video omitted", "sticker omitted", "audio omitted", "document omitted", "GIF omitted", "‎image omitted"))
        db_unique_senders = len({m.sender for m in total_rows if m.sender})
        db_null_timestamps = sum(1 for m in total_rows if m.timestamp is None)
        
        print(f"DB Total rows: {db_total_messages}")
        print(f"DB System rows (sender=''): {db_system_messages}")
        print(f"DB Null timestamps: {db_null_timestamps}")
        print(f"DB Media rows (approximate from content): {db_media_messages}")
        print(f"DB Unique senders: {db_unique_senders}")

if __name__ == "__main__":
    asyncio.run(main())
