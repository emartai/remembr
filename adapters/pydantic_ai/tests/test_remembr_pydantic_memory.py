from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.pydantic_ai.remembr_pydantic_memory import (
    RemembrMemoryDep,
    RemembrMemoryTools,
    RunContext,
    create_remembr_agent,
    remembr_system_prompt,
)


@dataclass
class _Session:
    session_id: str


@dataclass
class _Episode:
    episode_id: str


class _ResultItem:
    def __init__(self, episode_id: str, content: str, role: str = "user"):
        self.episode_id = episode_id
        self.content = content
        self.role = role
        self.score = 1.0
        self.created_at = datetime.now(timezone.utc)


class _SearchResult:
    def __init__(self, results):
        self.results = results


class FakeRemembrClient:
    def __init__(self):
        self.counter = 0
        self.sessions: dict[str, list[dict]] = {}
        self.deleted: set[str] = set()
        self.slow_search = False

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Session(sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        eid = f"e-{idx}"
        self.sessions[session_id].append({"episode_id": eid, "content": content, "role": role})
        return _Episode(eid)

    async def search(self, query, session_id=None, limit=5, mode="hybrid"):
        if self.slow_search:
            time.sleep(2.2)
        q = query.lower()
        rows = [
            _ResultItem(x["episode_id"], x["content"], x["role"])
            for x in self.sessions.get(session_id, [])
            if q.split()[0] in x["content"].lower()
        ]
        return _SearchResult(rows[:limit])

    async def forget_episode(self, episode_id):
        self.deleted.add(episode_id)


def test_tools_store_search_forget() -> None:
    client = FakeRemembrClient()
    sid = "s-1"
    client.sessions[sid] = []
    dep = RemembrMemoryDep(client=client, session_id=sid)
    ctx = RunContext(deps=dep)

    stored = RemembrMemoryTools.store_memory(ctx, "User likes Python", tags=["pref"])
    assert "Stored memory" in stored

    found = RemembrMemoryTools.search_memory(ctx, "User")
    assert "Relevant memories:" in found

    episode_id = next(iter(client.sessions[sid]))["episode_id"]
    msg = RemembrMemoryTools.forget_memory(ctx, episode_id)
    assert episode_id in msg
    assert episode_id in client.deleted


def test_system_prompt_times_out_within_two_secondsish() -> None:
    client = FakeRemembrClient()
    sid = "s-1"
    client.sessions[sid] = [{"episode_id": "e-1", "content": "Preference: concise", "role": "user"}]
    client.slow_search = True

    dep = RemembrMemoryDep(client=client, session_id=sid)
    ctx = RunContext(deps=dep)

    started = time.monotonic()
    prompt = remembr_system_prompt(ctx)
    elapsed = time.monotonic() - started

    assert "timed out" in prompt.lower()
    assert elapsed < 2.5


def test_create_agent_passes_kwargs_and_registers_tools(monkeypatch) -> None:
    import adapters.pydantic_ai.remembr_pydantic_memory as mod

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

        async def forget_episode(self, *args, **kwargs):
            return await fake_client.forget_episode(*args, **kwargs)

    monkeypatch.setitem(__import__("sys").modules, "remembr", type("M", (), {"RemembrClient": FakeClientCtor}))

    agent = create_remembr_agent(
        model="test-model",
        system_prompt="base",
        api_key="k",
        retries=3,
    )

    assert hasattr(agent, "remembr_deps")
    assert agent.kwargs.get("retries") == 3
    assert len(agent.tools) == 3
