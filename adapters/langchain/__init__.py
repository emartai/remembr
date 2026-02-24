from __future__ import annotations

"""LangChain adapter package for Remembr."""

from .remembr_memory import RemembrMemory


def create_langchain_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    return RemembrMemory(client=client, session_id=session_id, **kwargs)


__all__ = ["RemembrMemory", "create_langchain_memory"]
