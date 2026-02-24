from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.langgraph.remembr_langgraph_memory import (
    RemembrLangGraphCheckpointer,
    RemembrLangGraphMemory,
    add_remembr_to_graph,
)


@dataclass
class _Session:
    session_id: str


@dataclass
class _Episode:
    episode_id: str
    session_id: str
    role: str
    content: str
    created_at: datetime
    metadata: dict | None = None


class _SearchResultItem:
    def __init__(self, episode_id: str, content: str, role: str):
        self.episode_id = episode_id
        self.content = content
        self.role = role
        self.score = 1.0
        self.created_at = datetime.now(timezone.utc)


class _SearchResponse:
    def __init__(self, results):
        self.results = results


class FakeRemembrClient:
    def __init__(self):
        self.counter = 0
        self.sessions: dict[str, list[dict]] = {}

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Session(session_id=sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        self.sessions[session_id].append(
            {
                "episode_id": f"e-{idx}",
                "content": content,
                "role": role,
                "metadata": metadata or {},
            }
        )

    async def search(self, query, session_id=None, limit=20, **kwargs):
        q = query.lower()
        results = [
            _SearchResultItem(item["episode_id"], item["content"], item["role"])
            for item in self.sessions.get(session_id, [])
            if q in item["content"].lower()
        ]
        return _SearchResponse(results[:limit])

    async def get_session_history(self, session_id, limit=500):
        return [
            _Episode(
                episode_id=item["episode_id"],
                session_id=session_id,
                role=item["role"],
                content=item["content"],
                metadata=item.get("metadata"),
                created_at=datetime.now(timezone.utc),
            )
            for item in self.sessions.get(session_id, [])[:limit]
        ]


class FakeGraph:
    def __init__(self):
        self.nodes = {"agent": lambda s, c: s}
        self.edges = [("agent", "__end__")]

    def add_node(self, name, fn):
        self.nodes[name] = fn

    def add_edge(self, src, dst):
        self.edges.append((src, dst))


def test_load_memories_adds_context_key_purely() -> None:
    client = FakeRemembrClient()
    memory = RemembrLangGraphMemory(client=client)
    memory._store("Paris is in France", role="assistant")

    state = {"messages": [{"role": "user", "content": "Paris"}], "x": 1}
    updated = memory.load_memories(state, config={"configurable": {"thread_id": "t-1"}})

    assert "remembr_context" in updated
    assert "Paris" in updated["remembr_context"]
    assert state == {"messages": [{"role": "user", "content": "Paris"}], "x": 1}


def test_save_memories_stores_latest_exchange_and_passthrough() -> None:
    client = FakeRemembrClient()
    memory = RemembrLangGraphMemory(client=client)
    state = {
        "messages": [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]
    }

    returned = memory.save_memories(state, config={"configurable": {"thread_id": "thread-a"}})

    assert returned is state
    assert len(client.sessions[memory.session_id]) == 2


def test_add_remembr_to_graph_wires_nodes() -> None:
    client = FakeRemembrClient()
    graph = FakeGraph()

    out = add_remembr_to_graph(graph, client=client)

    assert out is graph
    assert "remembr_load_memories" in graph.nodes
    assert "remembr_save_memories" in graph.nodes
    assert ("__start__", "remembr_load_memories") in graph.edges
    assert ("remembr_save_memories", "__end__") in graph.edges


def test_checkpointer_put_get_and_list_by_thread() -> None:
    client = FakeRemembrClient()
    cp = RemembrLangGraphCheckpointer(client=client)

    cfg1 = {"configurable": {"thread_id": "thread-1"}}
    cfg2 = {"configurable": {"thread_id": "thread-2"}}

    cp.put(cfg1, {"id": 1, "state": "alpha"}, {"step": 1})
    cp.put(cfg1, {"id": 2, "state": "beta"}, {"step": 2})
    cp.put(cfg2, {"id": 3, "state": "gamma"}, {"step": 1})

    latest = cp.get(cfg1)
    assert latest is not None
    assert latest["id"] == 2

    listed = list(cp.list(cfg1))
    assert len(listed) == 2
