"""Conversation chunking service for memory retrieval."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from backend.app.database.models import Message
from backend.app.rag.vector_store import VectorDocument


class ConversationChunker:
    """Group chronological messages into discrete semantic conversation chunks.
    
    A chunk boundary occurs when there is a significant gap in time between
    messages (e.g. 30 minutes) or when the chunk exceeds a target character
    limit. Individual messages are never split.
    """

    def __init__(self, gap_minutes: int = 30, max_characters: int = 3000) -> None:
        self.gap_threshold = timedelta(minutes=gap_minutes)
        self.max_characters = max_characters
        self.media_placeholders = {
            "<Media omitted>", "image omitted", "video omitted", 
            "sticker omitted", "audio omitted", "document omitted", 
            "GIF omitted", "‎image omitted", "[Call]"
        }

    def _is_skipping(self, message: Message) -> bool:
        """Determine if a message should be excluded from semantic indexing."""
        if not message.sender:
            # System message or encryption notice
            return True
        if message.content.strip() in self.media_placeholders:
            # Media placeholder
            return True
        return False

    def _generate_chunk_id(self, messages: list[Message]) -> str:
        """Generate a stable, deterministic ID for a chunk based on its messages."""
        if not messages:
            return ""
        
        # We hash the source_ids to ensure stable chunk IDs even if re-indexed.
        # This prevents duplicate indexing of the same conversation.
        h = hashlib.sha256()
        for msg in messages:
            h.update(str(msg.id).encode("utf-8"))
        
        return f"chunk:{h.hexdigest()[:16]}"

    def create_chunks(self, messages: list[Message]) -> list[VectorDocument]:
        """Convert a list of chronologically ordered messages into chunks."""
        chunks: list[VectorDocument] = []
        current_messages: list[Message] = []
        current_length = 0

        def flush_chunk() -> None:
            nonlocal current_messages, current_length
            if not current_messages:
                return

            chunk_id = self._generate_chunk_id(current_messages)
            content = "\n".join(f"{msg.sender}: {msg.content}" for msg in current_messages)
            
            start_timestamp = current_messages[0].timestamp
            end_timestamp = current_messages[-1].timestamp
            participants = sorted(list({msg.sender for msg in current_messages}))
            source_ids = [msg.id for msg in current_messages]
            
            metadata: dict[str, Any] = {
                "source_type": "conversation_chunk",
                "person_id": current_messages[0].person_id,
                "start_timestamp": start_timestamp.isoformat() if start_timestamp else None,
                "end_timestamp": end_timestamp.isoformat() if end_timestamp else None,
                "participants": ", ".join(participants),
                "message_count": len(current_messages),
                "first_message_id": source_ids[0],
                "last_message_id": source_ids[-1],
            }

            chunks.append(
                VectorDocument(
                    id=chunk_id,
                    content=content,
                    metadata=metadata,
                )
            )
            current_messages = []
            current_length = 0

        for message in messages:
            if self._is_skipping(message):
                continue

            formatted_msg = f"{message.sender}: {message.content}"
            msg_length = len(formatted_msg)

            # Check gap threshold if we have previous messages
            if current_messages and message.timestamp and current_messages[-1].timestamp:
                time_diff = message.timestamp - current_messages[-1].timestamp
                if time_diff > self.gap_threshold:
                    flush_chunk()

            # Check character limit (unless it's the very first message in the chunk)
            if current_messages and (current_length + msg_length + 1 > self.max_characters):
                flush_chunk()

            current_messages.append(message)
            current_length += msg_length + 1  # +1 for newline

        flush_chunk()
        return chunks
