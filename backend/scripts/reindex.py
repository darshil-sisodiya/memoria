"""CLI script to index or reindex WhatsApp messages into ChromaDB."""

import asyncio
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path

# Add the project root to sys.path so we can run the script directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import select

from backend.app.core.config import get_settings
from backend.app.core.logging import configure_logging
from backend.app.database.database import create_db_engine, create_session_factory
from backend.app.database.models import Person
from backend.app.rag.indexer import IndexerService
from backend.app.rag.real_embeddings import SentenceTransformerEmbeddingProvider
from backend.app.rag.vector_store import ChromaVectorStore


async def reindex_person(person_id: int) -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    engine = create_db_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    
    embedding_provider = SentenceTransformerEmbeddingProvider(settings.rag_embedding_model)
    vector_store = ChromaVectorStore(settings.chroma_path)
    
    indexer = IndexerService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    with session_factory() as session:
        if person_id == 0:
            # Reindex all
            logger.info("Fetching all people...")
            people = list(session.execute(select(Person)).scalars().all())
        else:
            person = session.get(Person, person_id)
            if not person:
                logger.error(f"Person ID {person_id} not found.")
                return
            people = [person]

        for p in people:
            logger.info(f"Indexing messages for person: {p.name} (ID: {p.id})")
            stats = await indexer.index_person_messages(session, p.id)
            logger.info(
                f"Finished {p.name} | Processed chunks: {stats['chunks_processed']} "
                f"| Indexed: {stats['chunks_indexed']} | Skipped (already exist): {stats['chunks_skipped']}"
            )


def main() -> None:
    parser = ArgumentParser(description="Reindex WhatsApp conversations into ChromaDB RAG index.")
    parser.add_argument(
        "--person-id", 
        type=int, 
        default=0, 
        help="Specific person ID to index. If 0, indexes all people."
    )
    args = parser.parse_args()
    
    asyncio.run(reindex_person(args.person_id))


if __name__ == "__main__":
    main()
