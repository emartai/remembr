from __future__ import annotations

"""Haystack adapter package for Remembr."""

from .remembr_haystack_memory import (
    RemembrConversationMemory,
    RemembrMemoryRetriever,
    RemembrMemoryWriter,
    build_remembr_rag_pipeline,
)


def create_haystack_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    if session_id is None:
        import asyncio

        session_id = asyncio.run(client.create_session(metadata={"source": "haystack_factory"})).session_id
    return RemembrConversationMemory(client=client, session_id=session_id, **kwargs)


__all__ = [
    "RemembrMemoryRetriever",
    "RemembrMemoryWriter",
    "RemembrConversationMemory",
    "build_remembr_rag_pipeline",
    "create_haystack_memory",
]
