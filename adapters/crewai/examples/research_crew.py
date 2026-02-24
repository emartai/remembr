"""CrewAI shared-memory example using Remembr.

Usage:
    PYTHONPATH=./sdk/python:. python adapters/crewai/examples/research_crew.py
"""

from __future__ import annotations

import os

from adapters.crewai.remembr_crew_memory import RemembrSharedCrewMemory
from remembr import RemembrClient


class DemoAgent:
    def __init__(self, role: str):
        self.role = role
        self.memory = None


class DemoCrew:
    def __init__(self, agents):
        self.agents = agents


def main() -> None:
    client = RemembrClient(api_key=os.environ["REMEMBR_API_KEY"])

    shared_memory = RemembrSharedCrewMemory(client=client, team_id="research-team-alpha")

    researcher = DemoAgent(role="Researcher")
    writer = DemoAgent(role="Writer")
    crew = DemoCrew([researcher, writer])
    shared_memory.inject_into_crew(crew)

    researcher.memory.save("The Eiffel Tower was completed in 1889.")

    writer_facts = writer.memory.search("Eiffel Tower")
    print(f"Shared team session: {shared_memory.long_term}")
    print("Writer retrieved facts:")
    for fact in writer_facts:
        print(f"- {fact.content}")


if __name__ == "__main__":
    main()
