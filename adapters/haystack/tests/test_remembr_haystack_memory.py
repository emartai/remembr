from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.haystack.remembr_haystack_memory import (
    RemembrConversationMemory,
    RemembrMemoryRetriever,
    RemembrMemoryWriter,
    build_remembr_rag_pipeline,
)


@dataclass
class _Session:
    session_id: str


@dataclass
class _Episode:
    episode_id: str


class _SearchItem:
    def __init__(self, episode_id: str, role: str, content: str):
        self.episode_id = episode_id
        self.role = role
        self.content = content
        self.score = 1.0
        self.created_at = datetime.now(timezone.utc)


class _SearchResult:
    def __init__(self, results):
        self.results = results


class FakeRemembrClient:
    def __init__(self):
        self.counter = 0
        self.sessions: dict[str, list[dict]] = {}
        self.deleted: list[str] = []

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Session(sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        eid = f"e-{idx}"
        self.sessions[session_id].append({"episode_id": eid, "role": role, "content": content})
        return _Episode(eid)

    async def search(self, query, session_id=None, limit=5, mode="hybrid"):
        q = query.lower()
        out = [
            _SearchItem(x["episode_id"], x["role"], x["content"])
            for x in self.sessions.get(session_id, [])
            if any(tok in x["content"].lower() for tok in q.split())
        ]
        return _SearchResult(out[:limit])

    async def forget_episode(self, episode_id):
        self.deleted.append(episode_id)


class _Msg:
    def __init__(self, role: str, text: str):
        self.role = role
        self.text = text


class DummyLLM:
    def run(self, prompt: str | None = None, **kwargs):
        return {"replies": "Remember this final reply."}


def test_retriever_and_writer_components_sync_run() -> None:
    client = FakeRemembrClient()
    import asyncio

    sid = asyncio.run(client.create_session()).session_id

    writer = RemembrMemoryWriter(client=client, default_session_id=sid)
    out = writer.run(content="Alice likes concise answers", tags=["pref"])
    assert out["stored"] is True

    retriever = RemembrMemoryRetriever(client=client, default_session_id=sid)
    got = retriever.run(query="Alice")
    assert got["episode_ids"]
    assert "Alice" in got["memories"][0]


def test_conversation_memory_write_retrieve_delete() -> None:
    import asyncio

    client = FakeRemembrClient()
    sid = asyncio.run(client.create_session()).session_id

    memory = RemembrConversationMemory(client=client, session_id=sid, retrieval_query="concise")
    memory.write_messages([_Msg("user", "Please be concise"), _Msg("assistant", "Sure, concise mode enabled")])

    retrieved = memory.retrieve(limit=5)
    assert len(retrieved) >= 1

    memory.delete_messages(["e-1", "e-2"])
    assert client.deleted == ["e-1", "e-2"]


def test_pipeline_factory_connects_all_required_components() -> None:
    import asyncio

    client = FakeRemembrClient()
    sid = asyncio.run(client.create_session()).session_id
    pipeline = build_remembr_rag_pipeline(client=client, llm_component=DummyLLM(), session_id=sid)

    assert "memory_retriever" in pipeline.components
    assert "prompt_builder" in pipeline.components
    assert "llm" in pipeline.components
    assert "memory_writer" in pipeline.components

    assert ("memory_retriever.memories", "prompt_builder.memories") in pipeline.connections
    assert ("prompt_builder", "llm") in pipeline.connections
    assert ("llm.replies", "memory_writer.content") in pipeline.connections
