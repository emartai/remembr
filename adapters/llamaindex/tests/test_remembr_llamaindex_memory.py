from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.llamaindex.remembr_llamaindex_memory import (
    ChatMessage,
    MessageRole,
    RemembrChatStore,
    RemembrMemoryBuffer,
    RemembrSemanticMemory,
)


@dataclass
class _Episode:
    episode_id: str
    session_id: str
    role: str
    content: str
    created_at: datetime


class _Result:
    def __init__(self, episode_id: str, content: str, role: str = "user", score: float = 1.0):
        self.episode_id = episode_id
        self.content = content
        self.role = role
        self.score = score
        self.created_at = datetime.now(timezone.utc)


class _SearchResult:
    def __init__(self, results):
        self.results = results


class _Session:
    def __init__(self, session_id: str):
        self.session_id = session_id


class FakeRemembrClient:
    def __init__(self):
        self.counter = 0
        self.sessions: dict[str, list[dict]] = {}

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Session(sid)

    async def get_session_history(self, session_id: str, limit: int = 200):
        items = self.sessions.get(session_id, [])[:limit]
        return [
            _Episode(
                episode_id=item["episode_id"],
                session_id=session_id,
                role=item["role"],
                content=item["content"],
                created_at=datetime.now(timezone.utc),
            )
            for item in items
        ]

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        self.sessions[session_id].append({"episode_id": f"e-{idx}", "content": content, "role": role})

    async def forget_session(self, session_id):
        self.sessions[session_id] = []

    async def search(self, query, session_id=None, limit=20, mode="hybrid", **kwargs):
        q = query.lower()
        found = [
            _Result(item["episode_id"], item["content"], item["role"])
            for item in self.sessions.get(session_id, [])
            if q in item["content"].lower()
        ]
        return _SearchResult(found[:limit])


def test_chat_store_is_drop_in_basic_flow() -> None:
    client = FakeRemembrClient()
    session = RemembrSemanticMemory.from_client(client).session_id
    store = RemembrChatStore(client)

    store.add_message(session, ChatMessage(role=MessageRole.USER, content="hello"))
    store.add_message(session, ChatMessage(role=MessageRole.ASSISTANT, content="hi there"))

    messages = store.get_messages(session)
    assert len(messages) == 2
    assert messages[0].content == "hello"

    store.delete_messages(session)
    assert store.get_messages(session) == []


def test_memory_buffer_get_uses_semantic_search_and_token_limit() -> None:
    client = FakeRemembrClient()
    session_id = RemembrSemanticMemory.from_client(client).session_id

    store = RemembrChatStore(client)
    store.add_message(session_id, ChatMessage(role=MessageRole.USER, content="timeout is 30 seconds"))
    store.add_message(session_id, ChatMessage(role=MessageRole.USER, content="retry count is 3"))

    memory = RemembrMemoryBuffer(client=client, session_id=session_id, token_limit=4)
    out = memory.get(input="timeout")

    assert len(out) == 1
    assert "timeout" in out[0].content


def test_semantic_memory_retriever_roundtrip() -> None:
    client = FakeRemembrClient()
    semantic = RemembrSemanticMemory.from_client(client)

    semantic.save_context({"input": "Use edge-case tests"}, {"output": "Will do"})
    retriever = semantic.as_retriever()
    docs = retriever.retrieve("edge-case")

    assert len(docs) >= 1
    assert "edge-case" in docs[0]["text"].lower()
