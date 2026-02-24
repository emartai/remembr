"""Pydantic AI Remembr DI example.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/pydantic_ai/examples/assistant.py
"""

from __future__ import annotations

import os

from adapters.pydantic_ai.remembr_pydantic_memory import (
    RemembrMemoryTools,
    RunContext,
    create_remembr_agent,
)


def main() -> None:
    agent = create_remembr_agent(
        model="openai:gpt-4o-mini",
        system_prompt="You are a helpful assistant.",
        api_key=os.environ["REMEMBR_API_KEY"],
    )

    deps = agent.remembr_deps
    ctx = RunContext(deps=deps)

    print(RemembrMemoryTools.store_memory(ctx, "User prefers concise answers.", tags=["preference"]))
    print(RemembrMemoryTools.search_memory(ctx, "user preferences"))
    print("Session:", deps.session_id)


if __name__ == "__main__":
    main()
