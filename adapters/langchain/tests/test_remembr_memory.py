from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone


# Provide lightweight LangChain stubs if langchain is not installed.
if "langchain.memory.chat_memory" not in sys.modules:
    langchain = types.ModuleType("langchain")
    memory = types.ModuleType("langchain.memory")
    chat_memory = types.ModuleType("langchain.memory.chat_memory")

    class BaseChatMemory:  # pragma: no cover - used only when langchain is absent
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    chat_memory.BaseChatMemory = BaseChatMemory
    memory.chat_memory = chat_memory
    langchain.memory = memory
    sys.modules["langchain"] = langchain
    sys.modules["langchain.memory"] = memory
    sys.modules["langchain.memory.chat_memory"] = chat_memory

if "langchain_core.messages" not in sys.modules:
    messages = types.ModuleType("langchain_core.messages")

    class _Message:  # pragma: no cover - used only when langchain is absent
        def __init__(self, content: str):
            self.content = content

    class HumanMessage(_Message):
        pass

    class AIMessage(_Message):
        pass

    messages.HumanMessage = HumanMessage
    messages.AIMessage = AIMessage
    sys.modules["langchain_core.messages"] = messages

from adapters.langchain.remembr_memory import RemembrMemory


@dataclass
class _Obj:
    session_id: str | None = None
    role: str | None = None
    content: str | None = None
    created_at: datetime | None = None


class FakeSearchResult:
    def __init__(self, episode_id: str, role: str, content: str):
        self.episode_id = episode_id
        self.role = role
        self.content = content
        self.score = 1.0
        self.tags = []
        self.created_at = datetime.now(timezone.utc)


class FakeSearchResponse:
    def __init__(self, results):
        self.results = results


class FakeRemembrClient:
    def __init__(self):
        self.sessions = {}
        self.counter = 0

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Obj(session_id=sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        record = {
            "episode_id": f"e-{len(self.sessions[session_id]) + 1}",
            "content": content,
            "role": role,
        }
        self.sessions[session_id].append(record)
        return _Obj(
            session_id=session_id,
            role=role,
            content=content,
            created_at=datetime.now(timezone.utc),
        )

    async def search(self, query, session_id=None, **kwargs):
        matches = [
            FakeSearchResult(r["episode_id"], r["role"], r["content"])
            for r in self.sessions.get(session_id, [])
            if query.lower().split()[0] in r["content"].lower()
        ]
        return FakeSearchResponse(matches)

    async def checkpoint(self, session_id):
        return {"ok": True, "session_id": session_id}

    async def forget_session(self, session_id):
        self.sessions[session_id] = []
        return {"deleted": True}


def test_memory_persists_across_separate_instances() -> None:
    client = FakeRemembrClient()

    memory_a = RemembrMemory(client=client)
    memory_a.save_context(
        {"input": "My favorite language is Python"},
        {"output": "Noted"},
    )

    memory_b = RemembrMemory(client=client, session_id=memory_a.session_id)
    loaded = memory_b.load_memory_variables({"input": "favorite"})

    assert memory_b.memory_key in loaded
    assert len(loaded["history"]) >= 1
    assert loaded["history"][0].content == "My favorite language is Python"


def test_memory_key_always_present_when_no_results() -> None:
    client = FakeRemembrClient()
    memory = RemembrMemory(client=client)

    loaded = memory.load_memory_variables({"input": "does-not-exist"})

    assert loaded == {"history": []}


def test_clear_forgets_session() -> None:
    client = FakeRemembrClient()
    memory = RemembrMemory(client=client)
    memory.save_context({"input": "hello"}, {"output": "hi"})

    memory.clear()

    assert client.sessions[memory.session_id] == []
