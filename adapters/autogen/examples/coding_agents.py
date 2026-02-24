"""AutoGen coding duo example with Remembr persistent memory.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/autogen/examples/coding_agents.py
"""

from __future__ import annotations

import os

from adapters.autogen.remembr_autogen_memory import RemembrAutoGenGroupChatMemory
from remembr import RemembrClient


class DemoAgent:
    def __init__(self, name: str):
        self.name = name


class DemoGroupChat:
    def __init__(self):
        self.messages = []

    def append(self, message, speaker=None):
        self.messages.append({"speaker": getattr(speaker, "name", "unknown"), "message": message})


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])
    memory = RemembrAutoGenGroupChatMemory(
        client=client,
        scope_metadata={"demo": "autogen-coding-agents"},
        max_context_tokens=200,
    )

    coder = DemoAgent("Coder")
    reviewer = DemoAgent("CodeReviewer")
    group_chat = DemoGroupChat()
    memory.attach_to_group_chat(group_chat)

    group_chat.append("Use type hints and docstrings in utility functions.", speaker=reviewer)
    group_chat.append("Implemented parser without docstrings.", speaker=coder)

    prior_feedback = memory.query_agent_memory("CodeReviewer", "type hints")
    print("Past reviewer feedback context:")
    print(prior_feedback)

    new_review = memory.inject_context_into_message(
        "Please review this updated parser implementation for quality."
    )
    print("\nInjected review prompt:\n")
    print(new_review)


if __name__ == "__main__":
    main()
