from __future__ import annotations

"""LangGraph adapter package for Remembr."""

from .remembr_langgraph_memory import (
    RemembrLangGraphCheckpointer,
    RemembrLangGraphMemory,
    add_remembr_to_graph,
)


def create_langgraph_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    return RemembrLangGraphMemory(client=client, session_id=session_id, **kwargs)


__all__ = [
    "RemembrLangGraphMemory",
    "add_remembr_to_graph",
    "RemembrLangGraphCheckpointer",
    "create_langgraph_memory",
]
