"""A real StateGraph writes an explicit finding; no reasoning-model call is needed."""

import json
import os
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from remembr import RemembrClient


class State(TypedDict):
    finding: str
    memory_id: str


def remember(state: State):
    client = RemembrClient(
        api_key=os.environ["REMEMBR_API_KEY"],
        base_url=os.getenv("REMEMBR_URL", "http://localhost:8000").rstrip("/")
        + "/api/v1",
    )
    memory = client.projects.store(
        os.environ["REMEMBR_SPACE_ID"],
        state["finding"],
        idempotency_key=os.environ["REMEMBR_DEMO_KEY"],
        source_ref="synthetic:langgraph-research",
        run_id="langgraph-independent-process",
    )
    return {"memory_id": memory["id"]}


if __name__ == "__main__":
    graph = StateGraph(State)
    graph.add_node("remember", remember)
    graph.add_edge(START, "remember")
    graph.add_edge("remember", END)
    result = graph.compile().invoke(
        {"finding": os.environ["REMEMBR_DEMO_FINDING"], "memory_id": ""}
    )
    print(json.dumps({"memory_id": result["memory_id"]}))
