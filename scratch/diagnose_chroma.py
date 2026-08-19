import asyncio
from backend.app.core.config import get_settings
from backend.app.rag.vector_store import ChromaVectorStore
from backend.app.rag.real_embeddings import SentenceTransformerEmbeddingProvider
import json

async def main():
    settings = get_settings()
    print(f"Chroma DB Path from settings: {settings.chroma_path}")
    
    # Instantiate the vector store
    store = ChromaVectorStore(settings.chroma_path)
    chroma_collection = store._get_collection("messages")
    count = chroma_collection.count()
    print(f"Collection Name: messages")
    print(f"Collection Count (documents): {count}")
    
    if count == 0:
        print("No documents found in the index.")
        return
        
    # Read one indexed document directly
    # Chroma returns a dict with 'ids', 'embeddings', 'metadatas', 'documents'
    res = chroma_collection.peek(limit=1)
    
    # We only care about structure, not content
    print("\n--- Document Structure ---")
    print(f"ID: {res['ids'][0]}")
    metadata = res['metadatas'][0] if res['metadatas'] else {}
    print(f"Metadata keys: {list(metadata.keys())}")
    print("Metadata types:")
    for k, v in metadata.items():
        print(f"  {k}: {type(v).__name__} (value: {v})")
    
    if res.get('embeddings') and res['embeddings']:
        print(f"Embedding dimension: {len(res['embeddings'][0])}")
    else:
        print("Embedding dimension: None found in peek()")

    # Step 3: Test Raw Vector Search
    print("\n--- Test Raw Vector Search ---")
    provider = SentenceTransformerEmbeddingProvider()
    query_embedding = await provider.embed_text("Ask a question about Darshil")
    print(f"Generated query embedding of dim {len(query_embedding)}")
    
    # No filter query
    no_filter_res = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, count),
        include=["documents", "metadatas", "distances"]
    )
    
    print(f"Raw no-filter result count: {len(no_filter_res['ids'][0])}")
    if no_filter_res['ids'][0]:
        print("Raw top-k distances/similarities:", no_filter_res['distances'][0])
        
    # Step 4 & 5: Filtered Query
    print("\n--- Test Filtered Query ---")
    filtered_res = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, count),
        include=["documents", "metadatas", "distances"],
        where={"$and": [{"source_type": "conversation_chunk"}, {"person_id": 4}]}
    )
    print(f"Filtered result count: {len(filtered_res['ids'][0])}")

    print("\n--- Test Filtered Query with person_id=0 ---")
    filtered_res_0 = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=min(5, count),
        include=["documents", "metadatas", "distances"],
        where={"$and": [{"source_type": "conversation_chunk"}, {"person_id": 0}]}
    )
    print(f"Filtered result count (person_id=0): {len(filtered_res_0['ids'][0])}")

if __name__ == '__main__':
    asyncio.run(main())
