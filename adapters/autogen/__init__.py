from __future__ import annotations

"""AutoGen adapter package for Remembr."""

from .remembr_autogen_memory import RemembrAutoGenGroupChatMemory, RemembrAutoGenMemory


def create_autogen_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    return RemembrAutoGenMemory(client=client, session_id=session_id, **kwargs)


__all__ = ["RemembrAutoGenMemory", "RemembrAutoGenGroupChatMemory", "create_autogen_memory"]
