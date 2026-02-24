from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from adapters.autogen.remembr_autogen_memory import RemembrAutoGenGroupChatMemory, RemembrAutoGenMemory


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
        self.fail_store = False
        self.fail_search = False

    async def create_session(self, metadata=None):
        self.counter += 1
        sid = f"s-{self.counter}"
        self.sessions[sid] = []
        return _Obj(session_id=sid)

    async def store(self, content, role="user", session_id=None, tags=None, metadata=None):
        if self.fail_store:
            raise RuntimeError("store unavailable")
        idx = len(self.sessions[session_id]) + 1
        self.sessions[session_id].append({"episode_id": f"e-{idx}", "content": content, "role": role})

    async def search(self, query, session_id=None, **kwargs):
        if self.fail_search:
            raise RuntimeError("search unavailable")
        q = query.lower()
        results = [
            _Result(item["episode_id"], item["content"], item["role"])
            for item in self.sessions.get(session_id, [])
            if q in item["content"].lower()
        ]
        return _SearchResponse(results)

    async def checkpoint(self, session_id):
        return {"checkpoint_id": "cp-1"}

    async def forget_session(self, session_id):
        self.sessions[session_id] = []


class FakeAgent:
    def __init__(self, name: str):
        self.name = name
        self.hooks: dict[str, callable] = {}

    def register_hook(self, hook_name: str, fn):
        self.hooks[hook_name] = fn


class FakeGroupChat:
    def __init__(self):
        self.messages = []

    def append(self, message, speaker=None):
        self.messages.append((speaker.name if speaker else "unknown", message))


class _Speaker:
    def __init__(self, name: str):
        self.name = name


def test_attach_to_agent_registers_hooks_and_injects_context() -> None:
    client = FakeRemembrClient()
    memory = RemembrAutoGenMemory(client=client, max_context_tokens=40)
    agent = FakeAgent(name="Coder")

    memory._safe_store(content="Remember coding style: add docstrings.", role="user")
    memory.attach_to_agent(agent)

    assert "process_message_before_send" in agent.hooks
    assert "process_message_after_receive" in agent.hooks

    outgoing = agent.hooks["process_message_before_send"]("Please review parser")
    assert "Relevant memory:" in outgoing


def test_hooks_fail_silently_when_store_or_search_unavailable() -> None:
    client = FakeRemembrClient()
    memory = RemembrAutoGenMemory(client=client)
    agent = FakeAgent(name="Reviewer")
    memory.attach_to_agent(agent)

    client.fail_store = True
    returned = agent.hooks["process_message_after_receive"]("hello")
    assert returned == "hello"

    client.fail_store = False
    client.fail_search = True
    injected = agent.hooks["process_message_before_send"]("check tests")
    assert injected == "check tests"


def test_group_chat_memory_stores_and_queries_by_agent_scope() -> None:
    client = FakeRemembrClient()
    memory = RemembrAutoGenGroupChatMemory(client=client)
    group_chat = FakeGroupChat()
    memory.attach_to_group_chat(group_chat)

    reviewer = _Speaker("CodeReviewer")
    coder = _Speaker("Coder")

    group_chat.append("Use stricter edge-case tests", speaker=reviewer)
    group_chat.append("Added tests for empty input", speaker=coder)

    reviewer_ctx = memory.query_agent_memory("CodeReviewer", "stricter")
    assert "CodeReviewer" in reviewer_ctx
    assert "stricter edge-case tests" in reviewer_ctx


def test_context_truncation_respects_max_context_tokens() -> None:
    client = FakeRemembrClient()
    memory = RemembrAutoGenMemory(client=client, max_context_tokens=4)
    memory._safe_store(content="one two three four five six", role="user")

    context = memory.get_relevant_context("one")
    assert len(context.split()) <= 4
