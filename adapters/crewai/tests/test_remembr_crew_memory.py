from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.crewai.remembr_crew_memory import RemembrCrewMemory, RemembrSharedCrewMemory


@dataclass
class _Obj:
    session_id: str | None = None


class _Result:
    def __init__(self, episode_id: str, content: str, role: str = "user"):
        self.episode_id = episode_id
        self.content = content
        self.role = role
        self.score = 1.0
        self.tags = []
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
        return _Obj(session_id=sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        idx = len(self.sessions[session_id]) + 1
        self.sessions[session_id].append({"episode_id": f"e-{idx}", "content": content, "role": role})

    async def search(self, query, session_id=None, **kwargs):
        q = query.lower()
        results = [
            _Result(item["episode_id"], item["content"], item["role"])
            for item in self.sessions.get(session_id, [])
            if q in item["content"].lower()
        ]
        return _SearchResponse(results)

    async def forget_session(self, session_id):
        self.sessions[session_id] = []


def test_save_writes_short_and_long_term() -> None:
    client = FakeRemembrClient()
    memory = RemembrCrewMemory(client=client, agent_id="a1", team_id="t1")

    memory.save("alpha fact")

    assert len(client.sessions[memory.short_term]) == 1
    assert len(client.sessions[memory.long_term]) == 1


def test_search_merges_deduplicates_and_reset_only_clears_short_term() -> None:
    client = FakeRemembrClient()
    memory = RemembrCrewMemory(client=client, agent_id="a1", team_id="t1")

    memory.save("Shared fact")
    memory._run(
        client.store(
            "Additional long-term detail",
            session_id=memory.long_term,
            role="user",
        )
    )
    matches = memory.search("shared")
    assert len(matches) == 1  # duplicated short/long entries dedupe

    long_term_matches = memory.search("additional")
    assert len(long_term_matches) == 1

    memory.reset()
    assert client.sessions[memory.short_term] == []
    assert len(client.sessions[memory.long_term]) == 2


def test_shared_memory_injection_and_cross_agent_access() -> None:
    client = FakeRemembrClient()
    shared = RemembrSharedCrewMemory(client=client, team_id="team-42")

    class Agent:
        def __init__(self):
            self.memory = None

    class Crew:
        def __init__(self):
            self.agents = [Agent(), Agent()]

    crew = Crew()
    shared.inject_into_crew(crew)

    crew.agents[0].memory.save("Researcher discovered: Mercury is the closest planet.")
    found = crew.agents[1].memory.search("Mercury")

    assert len(found) == 1
    assert "Mercury" in found[0].content
