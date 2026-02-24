"""LlamaIndex chat engine style example using RemembrMemoryBuffer.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/llamaindex/examples/chat_engine.py
"""

from __future__ import annotations

import os

from adapters.llamaindex.remembr_llamaindex_memory import RemembrMemoryBuffer
from remembr import RemembrClient


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])

    session_id = client.request("POST", "/sessions", json={"metadata": {"demo": "llamaindex-chat-engine"}})["session_id"]
    memory = RemembrMemoryBuffer(client=client, session_id=session_id, token_limit=64)

    memory.chat_store.add_message(session_id, type("Msg", (), {"role": "user", "content": "My API timeout is 30s"})())
    memory.chat_store.add_message(session_id, type("Msg", (), {"role": "assistant", "content": "Noted. Timeout=30s."})())

    retrieved = memory.get(input="What timeout did I set?")

    print("Session:", session_id)
    print("Retrieved semantic memory:")
    for msg in retrieved:
        print(f"- {msg.role}: {msg.content}")


if __name__ == "__main__":
    main()
