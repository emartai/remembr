"""Customer support memory example for OpenAI Agents SDK + Remembr.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/openai_agents/examples/customer_support.py
"""

from __future__ import annotations

import os

from adapters.openai_agents.remembr_openai_memory import RemembrMemoryTools, create_remembr_agent


def main() -> None:
    agent = create_remembr_agent(
        name="SupportAgent",
        instructions="Help users with ticket follow-ups and preferences.",
        model="gpt-4o-mini",
        api_key=os.environ["REMEMBR_API_KEY"],
    )

    session_id = agent.remembr_session_id
    print(RemembrMemoryTools.store_memory("User prefers email updates", session_id, tags="preference,support"))
    print(RemembrMemoryTools.store_memory("Ticket #1042: refund approved", session_id, tags="ticket"))

    print("\n--- Run 1 memory snapshot ---")
    print(RemembrMemoryTools.get_session_summary(session_id))

    print("\n--- Run 2 relevant memory ---")
    print(RemembrMemoryTools.search_memory("ticket refund", session_id))


if __name__ == "__main__":
    main()
