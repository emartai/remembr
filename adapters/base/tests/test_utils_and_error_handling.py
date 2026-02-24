from __future__ import annotations

from dataclasses import dataclass

from adapters.base.error_handling import RemembrError, with_remembr_fallback
from adapters.base.utils import (
    deduplicate_episodes,
    format_messages_for_llm,
    parse_role,
    scope_from_agent_metadata,
    truncate_to_token_limit,
)


@dataclass
class _Ep:
    episode_id: str
    role: str
    content: str


def test_parse_role_and_formatting_and_dedupe() -> None:
    episodes = [
        _Ep("e1", "Human", "Hello"),
        _Ep("e1", "human", "Hello duplicate"),
        _Ep("e2", "ai", "Hi"),
    ]
    uniq = deduplicate_episodes(episodes)
    assert len(uniq) == 2
    assert parse_role("Human") == "user"
    assert parse_role("ai") == "assistant"
    text = format_messages_for_llm(uniq)
    assert "User: Hello" in text
    assert "Assistant: Hi" in text


def test_scope_and_truncation() -> None:
    scoped = scope_from_agent_metadata({"team_id": "t1", "foo": "bar", "agent_id": "a1"})
    assert scoped == {"team_id": "t1", "agent_id": "a1"}
    assert truncate_to_token_limit("one two three", 2)


def test_fallback_decorator_returns_default() -> None:
    class Demo:
        @with_remembr_fallback(default_value={"ok": False})
        def fn(self):
            raise RemembrError("down")

    assert Demo().fn() == {"ok": False}
