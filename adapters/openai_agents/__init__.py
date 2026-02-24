"""OpenAI Agents adapter package for Remembr."""

from .remembr_openai_memory import (
    RemembrAgentHooks,
    RemembrHandoffMemory,
    RemembrMemoryTools,
    create_remembr_agent,
)


def create_openai_agents_memory(api_key: str, session_id: str | None = None, **kwargs):
    return create_remembr_agent(
        name=kwargs.pop("name", "RemembrAgent"),
        instructions=kwargs.pop("instructions", "You are a helpful assistant."),
        model=kwargs.pop("model", "gpt-4o-mini"),
        api_key=api_key,
        session_id=session_id,
        **kwargs,
    )


__all__ = [
    "RemembrMemoryTools",
    "RemembrAgentHooks",
    "RemembrHandoffMemory",
    "create_remembr_agent",
    "create_openai_agents_memory",
]
