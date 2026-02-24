from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.integration]


async def _create_session(client, tracked_sessions: list[str], label: str) -> str:
    session = await client.create_session(metadata={"source": "e2e", "label": label, "run_id": str(uuid.uuid4())})
    tracked_sessions.append(session.session_id)
    return session.session_id


@pytest.mark.asyncio
async def test_store_and_retrieve(e2e_client, tracked_sessions, tracked_episodes) -> None:
    session_id = await _create_session(e2e_client, tracked_sessions, "store-retrieve")

    payloads = [
        ("I prefer dark mode interfaces.", "user"),
        ("Your preference for dark mode has been saved.", "assistant"),
        ("My favorite database is PostgreSQL with pgvector.", "user"),
        ("I will use PostgreSQL and vector search for memory retrieval.", "assistant"),
        ("Reminder: summarize action items every Friday.", "user"),
    ]

    for content, role in payloads:
        episode = await e2e_client.store(content=content, role=role, session_id=session_id)
        tracked_episodes.append(episode.episode_id)

    result = await e2e_client.search(query="What database stack should I use for vectors?", session_id=session_id, limit=5)

    assert result.total >= 1
    assert any("postgresql" in item.content.lower() or "pgvector" in item.content.lower() for item in result.results)


@pytest.mark.asyncio
async def test_session_isolation(e2e_client, tracked_sessions, tracked_episodes) -> None:
    s1 = await _create_session(e2e_client, tracked_sessions, "isolation-a")
    s2 = await _create_session(e2e_client, tracked_sessions, "isolation-b")

    ep_a = await e2e_client.store(content="Session A secret: project codename Zephyr.", role="user", session_id=s1)
    ep_b = await e2e_client.store(content="Session B secret: project codename Atlas.", role="user", session_id=s2)
    tracked_episodes.extend([ep_a.episode_id, ep_b.episode_id])

    search_a = await e2e_client.search(query="Atlas", session_id=s1, limit=5)
    search_b = await e2e_client.search(query="Zephyr", session_id=s2, limit=5)

    assert all("atlas" not in hit.content.lower() for hit in search_a.results)
    assert all("zephyr" not in hit.content.lower() for hit in search_b.results)


@pytest.mark.asyncio
async def test_checkpoint_restore(e2e_client, tracked_sessions, tracked_episodes) -> None:
    session_id = await _create_session(e2e_client, tracked_sessions, "checkpoint-restore")

    base_messages = [
        "Use concise responses.",
        "Call me Priya.",
    ]
    for msg in base_messages:
        ep = await e2e_client.store(content=msg, role="user", session_id=session_id)
        tracked_episodes.append(ep.episode_id)

    checkpoint = await e2e_client.checkpoint(session_id)

    extra = await e2e_client.store(content="Temporary preference: pirate voice.", role="user", session_id=session_id)
    tracked_episodes.append(extra.episode_id)

    await e2e_client.restore(session_id, checkpoint.checkpoint_id)

    history = await e2e_client.get_session_history(session_id=session_id, limit=50)
    text_history = [item.content for item in history]

    assert any("Use concise responses." == line for line in text_history)
    assert any("Call me Priya." == line for line in text_history)
    assert all("pirate voice" not in line.lower() for line in text_history)


@pytest.mark.asyncio
async def test_forget_episode(e2e_client, tracked_sessions) -> None:
    session_id = await _create_session(e2e_client, tracked_sessions, "forget-episode")
    episode = await e2e_client.store(content="Delete this single memory entry.", role="user", session_id=session_id)

    before = await e2e_client.search(query="single memory", session_id=session_id, limit=5)
    assert any(hit.episode_id == episode.episode_id for hit in before.results)

    await e2e_client.forget_episode(episode.episode_id)

    after = await e2e_client.search(query="single memory", session_id=session_id, limit=5)
    assert all(hit.episode_id != episode.episode_id for hit in after.results)


@pytest.mark.asyncio
async def test_forget_session(e2e_client, tracked_sessions, tracked_episodes) -> None:
    session_id = await _create_session(e2e_client, tracked_sessions, "forget-session")

    for idx in range(3):
        ep = await e2e_client.store(content=f"Session scoped note #{idx}", role="user", session_id=session_id)
        tracked_episodes.append(ep.episode_id)

    before = await e2e_client.get_session_history(session_id=session_id, limit=20)
    assert len(before) >= 3

    await e2e_client.forget_session(session_id)

    after = await e2e_client.get_session_history(session_id=session_id, limit=20)
    assert len(after) == 0
