"""Pydantic AI adapter package for Remembr."""

from .remembr_pydantic_memory import (
    RemembrMemoryDep,
    RemembrMemoryTools,
    create_remembr_agent,
    remembr_system_prompt,
)


def create_pydantic_ai_memory(api_key: str, session_id: str | None = None, **kwargs):
    return create_remembr_agent(model=kwargs.pop("model", "openai:gpt-4o-mini"), system_prompt=kwargs.pop("system_prompt", None), api_key=api_key, session_id=session_id, **kwargs)


__all__ = [
    "RemembrMemoryDep",
    "RemembrMemoryTools",
    "remembr_system_prompt",
    "create_remembr_agent",
    "create_pydantic_ai_memory",
]
