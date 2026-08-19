"""Context builder for injecting retrieved history into LLM prompts."""

from __future__ import annotations

from backend.app.rag.vector_store import VectorSearchResult


class ContextBuilder:
    """Builds the system prompt context using retrieved history."""

    def __init__(self, system_instruction: str = "You are a local AI preserving a person's conversational style.") -> None:
        self.system_instruction = system_instruction

    def build_system_prompt(self, retrieved_history: list[VectorSearchResult]) -> str:
        """Construct the final system prompt with bounded context."""
        
        prompt_parts = [self.system_instruction]
        
        if retrieved_history:
            prompt_parts.append("\nRELEVANT CONVERSATION HISTORY:")
            prompt_parts.append("Use the following historical conversation chunks as factual context to answer the user.")
            prompt_parts.append("Do not invent historical context that is not supported by these chunks.")
            prompt_parts.append("")
            
            # Sort by ascending chronological order if possible (using metadata), otherwise keep retrieval order.
            # Usually end_timestamp or start_timestamp is present.
            try:
                sorted_history = sorted(
                    retrieved_history,
                    key=lambda x: x.metadata.get("start_timestamp") or ""
                )
            except Exception:
                sorted_history = retrieved_history

            for i, chunk in enumerate(sorted_history, start=1):
                start = chunk.metadata.get("start_timestamp", "Unknown time")
                end = chunk.metadata.get("end_timestamp", "Unknown time")
                prompt_parts.append(f"--- Historical Chunk {i} ({start} to {end}) ---")
                prompt_parts.append(chunk.content.strip())
                prompt_parts.append("")
                
        return "\n".join(prompt_parts).strip()
