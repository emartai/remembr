"""Run a minimal LangChain agent wired to RemembrMemory.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/langchain/examples/basic_agent.py
"""

from __future__ import annotations

import os

from langchain.agents import AgentType, initialize_agent
from langchain.tools import Tool

from adapters.langchain.remembr_memory import RemembrMemory
from remembr import RemembrClient

try:
    from langchain_core.language_models.fake_chat_models import FakeListChatModel
except Exception:  # pragma: no cover - example fallback
    from langchain_community.chat_models.fake import FakeListChatModel


def echo_tool(text: str) -> str:
    return f"echo:{text}"


def build_agent(memory: RemembrMemory):
    llm = FakeListChatModel(
        responses=[
            "Got it — I'll remember that.",
            "From what you told me before, your favorite color is blue.",
        ]
    )
    tools = [Tool(name="Echo", func=echo_tool, description="Echoes text")]
    return initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        memory=memory,
        verbose=True,
    )


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])

    first_memory = RemembrMemory(client=client, scope_metadata={"demo": "langchain-basic-agent"})
    first_agent = build_agent(first_memory)
    first_agent.invoke({"input": "Remember this: my favorite color is blue."})

    # A separate invocation (new memory + new agent instance) reuses the same session.
    second_memory = RemembrMemory(client=client, session_id=first_memory.session_id)
    second_agent = build_agent(second_memory)
    response = second_agent.invoke({"input": "What's my favorite color?"})

    print("\nSession ID:", first_memory.session_id)
    print("Second invocation output:", response["output"])


if __name__ == "__main__":
    main()
