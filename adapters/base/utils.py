"""Shared adapter utility helpers."""

from __future__ import annotations

from typing import Any

try:
    import tiktoken
except Exception:  # pragma: no cover
    tiktoken = None


def parse_role(role_str: str) -> str:
    value = (role_str or "").strip().lower()
    if value in {"human", "user"}:
        return "user"
    if value in {"assistant", "ai", "model"}:
        return "assistant"
    if value in {"system"}:
        return "system"
    return value or "user"


def format_messages_for_llm(episodes: list[Any]) -> str:
    lines: list[str] = []
    for item in episodes:
        role = parse_role(getattr(item, "role", "user"))
        content = getattr(item, "content", "")
        lines.append(f"{role.title()}: {content}")
    return "\n".join(lines)


def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    if not text:
        return ""

    if tiktoken is None:
        words = text.split()
        return " ".join(words[:max_tokens])

    try:
        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text)
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens])
    except Exception:
        words = text.split()
        return " ".join(words[:max_tokens])


def scope_from_agent_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if not metadata:
        return {}
    scoped: dict[str, Any] = {}
    for key in ("org_id", "team_id", "user_id", "agent_id", "session_id", "thread_id"):
        if key in metadata and metadata[key] is not None:
            scoped[key] = metadata[key]
    return scoped


def deduplicate_episodes(episodes: list[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for episode in episodes:
        eid = str(getattr(episode, "episode_id", ""))
        if eid and eid in seen:
            continue
        if eid:
            seen.add(eid)
        out.append(episode)
    return out
