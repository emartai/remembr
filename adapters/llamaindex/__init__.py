from __future__ import annotations

"""LlamaIndex adapter package for Remembr."""

from .remembr_llamaindex_memory import RemembrChatStore, RemembrMemoryBuffer, RemembrSemanticMemory


def create_llamaindex_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    sid = session_id
    if sid is None:
        sid = RemembrSemanticMemory.from_client(client).session_id
    return RemembrMemoryBuffer(client=client, session_id=sid, **kwargs)


__all__ = ["RemembrChatStore", "RemembrMemoryBuffer", "RemembrSemanticMemory", "create_llamaindex_memory"]
