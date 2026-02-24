"""LangGraph-style research agent example using Remembr memory nodes.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/langgraph/examples/research_agent.py
"""

from __future__ import annotations

import os

from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphMemory
from remembr import RemembrClient


def run_invocation(memory: RemembrLangGraphMemory, user_question: str, tool_result: str) -> dict:
    state = {
        "messages": [
            {"role": "user", "content": user_question},
            {"role": "assistant", "content": tool_result},
        ]
    }
    state = memory.load_memories(state, config={"configurable": {"thread_id": "research-thread"}})
    memory.save_memories(state, config={"configurable": {"thread_id": "research-thread"}})
    return state


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])
    memory = RemembrLangGraphMemory(client=client, scope_metadata={"demo": "langgraph-research-agent"})

    run_invocation(memory, "Find latest release year of Python", "Tool: Python 3.12 released in 2023")
    second = run_invocation(memory, "What did the tool return earlier?", "Tool: previously noted Python 3.12 (2023)")

    print("Session:", memory.session_id)
    print("Injected context on second invocation:")
    print(second[memory.as_state_key])


if __name__ == "__main__":
    main()
