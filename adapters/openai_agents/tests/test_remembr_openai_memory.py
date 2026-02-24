from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.openai_agents.remembr_openai_memory import (
    RemembrAgentHooks,
    RemembrHandoffMemory,
    RemembrMemoryTools,
    create_remembr_agent,
)


@dataclass
class _Session:
    session_id: str


@dataclass
class _Episode:
    episode_id: str


class _HistoryItem:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
        self.created_at = datetime.now(timezone.utc)


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

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Session(sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        eid = f"e-{idx}"
        self.sessions[session_id].append({"episode_id": eid, "role": role, "content": content, "metadata": metadata or {}})
        return _Episode(eid)

    async def search(self, query, session_id=None, limit=8, mode="hybrid"):
        q = query.lower()
        out = [
            _SearchItem(x["episode_id"], x["role"], x["content"])
            for x in self.sessions.get(session_id, [])
            if any(tok in x["content"].lower() for tok in q.split())
        ]
        return _SearchResult(out[:limit])

    async def get_session_history(self, session_id, limit=30):
        return [_HistoryItem(x["role"], x["content"]) for x in self.sessions.get(session_id, [])[:limit]]


class _Tool:
    name = "memory_search"


class _Agent:
    name = "SupportAgent"


class _Source:
    name = "RouterAgent"


class _Handoff:
    def __init__(self):
        self.on_handoff = None


def test_memory_tools_search_store_summary() -> None:
    client = FakeRemembrClient()
    session = asyncio.run(client.create_session())
    RemembrMemoryTools.configure(client)

    msg = RemembrMemoryTools.store_memory("customer likes sms", session.session_id, tags="pref")
    assert "Stored memory" in msg

    found = RemembrMemoryTools.search_memory("customer", session.session_id)
    assert "Relevant memories:" in found

    summary = RemembrMemoryTools.get_session_summary(session.session_id)
    assert "summary" in summary.lower()


def test_hooks_log_non_blocking_events() -> None:
    client = FakeRemembrClient()
    session = asyncio.run(client.create_session())
    hooks = RemembrAgentHooks(client=client, session_id=session.session_id)

    hooks.on_tool_end(None, _Agent(), _Tool(), "ok")
    hooks.on_handoff(None, _Agent(), _Source())
    hooks.on_agent_end(None, _Agent(), "final")

    # allow fire-and-forget thread/loop tasks to complete
    import time

    time.sleep(0.05)

    assert len(client.sessions[session.session_id]) >= 3


def test_handoff_memory_thread_safe_and_attach() -> None:
    client = FakeRemembrClient()
    session = asyncio.run(client.create_session())
    handoff_mem = RemembrHandoffMemory(client=client, session_id=session.session_id)

    handoff_mem.store_before_handoff("AgentA", "customer asked about refund")
    import time

    time.sleep(0.03)
    injected = handoff_mem.inject_after_handoff("AgentB")
    assert "handoff" in injected.lower() or injected == ""

    h = _Handoff()
    out = handoff_mem.attach_to_handoff(h)
    assert out is h
    assert callable(h.on_handoff)


def test_factory_creates_agent_with_tools_and_hooks(monkeypatch) -> None:
    import sys

    class FakeAgent:
        def __init__(self, name, instructions, model, tools=None, hooks=None, **kwargs):
            self.name = name
            self.instructions = instructions
            self.model = model
            self.tools = tools or []
            self.hooks = hooks
            self.kwargs = kwargs

    fake_client = FakeRemembrClient()

    class FakeClientCtor:
        def __init__(self, api_key):
            self.api_key = api_key

        async def create_session(self, metadata=None):
            return await fake_client.create_session(metadata)

        async def search(self, *args, **kwargs):
            return await fake_client.search(*args, **kwargs)

        async def store(self, *args, **kwargs):
            return await fake_client.store(*args, **kwargs)

        async def get_session_history(self, *args, **kwargs):
            return await fake_client.get_session_history(*args, **kwargs)

    monkeypatch.setitem(sys.modules, "remembr", type("M", (), {"RemembrClient": FakeClientCtor}))

    import adapters.openai_agents.remembr_openai_memory as mod

    monkeypatch.setattr(mod, "Agent", FakeAgent)

    agent = create_remembr_agent(
        name="Support",
        instructions="help users",
        model="gpt-test",
        api_key="rk",
        temperature=0.2,
    )

    assert agent.name == "Support"
    assert "Memory Context" in agent.instructions
    assert len(agent.tools) >= 3
    assert hasattr(agent, "remembr_session_id")
    assert agent.kwargs["temperature"] == 0.2
