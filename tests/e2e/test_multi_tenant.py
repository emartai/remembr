from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_org_isolation(org_a_client, org_b_client) -> None:
    run_id = str(uuid.uuid4())

    session_a = await org_a_client.create_session(metadata={"scope": "org-a", "run_id": run_id})
    session_b = await org_b_client.create_session(metadata={"scope": "org-b", "run_id": run_id})

    await org_a_client.store(content="Org A secret roadmap token: ALPHA-42", role="user", session_id=session_a.session_id)

    a_results = await org_a_client.search(query="ALPHA-42", session_id=session_a.session_id, limit=5)
    b_results = await org_b_client.search(query="ALPHA-42", session_id=session_b.session_id, limit=5)

    assert any("alpha-42" in item.content.lower() for item in a_results.results)
    assert all("alpha-42" not in item.content.lower() for item in b_results.results)


@pytest.mark.asyncio
async def test_team_scope(e2e_client, tracked_sessions, tracked_episodes) -> None:
    team_a_s1 = await e2e_client.create_session(metadata={"team_id": "team-a", "agent_id": "agent-1", "run_id": str(uuid.uuid4())})
    team_a_s2 = await e2e_client.create_session(metadata={"team_id": "team-a", "agent_id": "agent-2", "run_id": str(uuid.uuid4())})
    team_b_s1 = await e2e_client.create_session(metadata={"team_id": "team-b", "agent_id": "agent-3", "run_id": str(uuid.uuid4())})
    tracked_sessions.extend([team_a_s1.session_id, team_a_s2.session_id, team_b_s1.session_id])

    ep = await e2e_client.store(
        content="Shared team-a operating preference: always include rollback plans.",
        role="user",
        session_id=team_a_s1.session_id,
        metadata={"team_id": "team-a", "visibility": "team"},
    )
    tracked_episodes.append(ep.episode_id)

    team_a_visible = await e2e_client.search(query="rollback plans", session_id=team_a_s1.session_id, limit=5)
    team_b_visible = await e2e_client.search(query="rollback plans", session_id=team_b_s1.session_id, limit=5)

    assert any("rollback plans" in item.content.lower() for item in team_a_visible.results)
    assert all("rollback plans" not in item.content.lower() for item in team_b_visible.results)


@pytest.mark.asyncio
async def test_agent_private(e2e_client, tracked_sessions, tracked_episodes) -> None:
    agent_1 = await e2e_client.create_session(metadata={"agent_id": "agent-private-1", "run_id": str(uuid.uuid4())})
    agent_2 = await e2e_client.create_session(metadata={"agent_id": "agent-private-2", "run_id": str(uuid.uuid4())})
    tracked_sessions.extend([agent_1.session_id, agent_2.session_id])

    ep = await e2e_client.store(
        content="Private to agent-private-1: rotate credentials monthly.",
        role="user",
        session_id=agent_1.session_id,
        metadata={"agent_id": "agent-private-1", "visibility": "private"},
    )
    tracked_episodes.append(ep.episode_id)

    owner_view = await e2e_client.search(query="rotate credentials", session_id=agent_1.session_id, limit=5)
    other_view = await e2e_client.search(query="rotate credentials", session_id=agent_2.session_id, limit=5)

    assert any("rotate credentials" in item.content.lower() for item in owner_view.results)
    assert all("rotate credentials" not in item.content.lower() for item in other_view.results)
