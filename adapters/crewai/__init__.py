from __future__ import annotations

"""CrewAI adapter package for Remembr."""

from .remembr_crew_memory import RemembrCrewMemory, RemembrSharedCrewMemory


def create_crewai_memory(api_key: str, session_id: str | None = None, **kwargs):
    from remembr import RemembrClient

    client = RemembrClient(api_key=api_key)
    if session_id and "short_term_session_id" not in kwargs:
        kwargs["short_term_session_id"] = session_id
    return RemembrCrewMemory(client=client, **kwargs)


__all__ = ["RemembrCrewMemory", "RemembrSharedCrewMemory", "create_crewai_memory"]
