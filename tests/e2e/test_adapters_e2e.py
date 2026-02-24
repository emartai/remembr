from __future__ import annotations

import time
import uuid

import pytest

from adapters.autogen.remembr_autogen_memory import RemembrAutoGenMemory
from adapters.crewai.remembr_crew_memory import RemembrCrewMemory
from adapters.haystack.remembr_haystack_memory import RemembrConversationMemory, RemembrMemoryRetriever, RemembrMemoryWriter
from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphCheckpointer
from adapters.llamaindex.remembr_llamaindex_memory import RemembrSemanticMemory
from adapters.openai_agents.remembr_openai_memory import RemembrAgentHooks, RemembrMemoryTools
from adapters.pydantic_ai.remembr_pydantic_memory import RemembrMemoryDep, RemembrMemoryTools as PydanticTools

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_langchain_persistence(e2e_client, tracked_sessions) -> None:
    pytest.importorskip("langchain")
    pytest.importorskip("langchain_core")
    from adapters.langchain.remembr_memory import RemembrMemory

    memory = RemembrMemory(client=e2e_client)
    tracked_sessions.append(memory.session_id)

    memory.save_context({"input": "My preferred editor is Neovim."}, {"output": "Got it."})
    loaded = memory.load_memory_variables({"input": "What editor do I use?"})

    assert any("neovim" in msg.content.lower() for msg in loaded["history"])


@pytest.mark.asyncio
async def test_langgraph_checkpointer(e2e_client, tracked_sessions) -> None:
    checkpointer = RemembrLangGraphCheckpointer(client=e2e_client)
    tracked_sessions.append(checkpointer.session_id)

    cfg = {"configurable": {"thread_id": f"thread-{uuid.uuid4()}"}}
    checkpointer.put(cfg, {"step": 1, "state": "alpha"}, {"stage": "draft"})
    checkpointer.put(cfg, {"step": 2, "state": "beta"}, {"stage": "final"})

    latest = checkpointer.get(cfg)
    assert latest is not None
    assert latest["state"] == "beta"


@pytest.mark.asyncio
async def test_crewai_shared_memory(e2e_client, tracked_sessions) -> None:
    shared_session = await e2e_client.create_session(metadata={"source": "e2e-crewai", "run_id": str(uuid.uuid4())})
    tracked_sessions.append(shared_session.session_id)

    crew_a = RemembrCrewMemory(
        client=e2e_client,
        agent_id="agent-a",
        team_id="team-1",
        short_term_session_id=shared_session.session_id,
        long_term_session_id=shared_session.session_id,
    )
    crew_b = RemembrCrewMemory(
        client=e2e_client,
        agent_id="agent-b",
        team_id="team-1",
        short_term_session_id=shared_session.session_id,
        long_term_session_id=shared_session.session_id,
    )

    crew_a.save("Crew runbook says escalate DB latency incidents within 10 minutes")
    results = crew_b.search("DB latency incidents")

    assert any("latency" in item.content.lower() for item in results)


@pytest.mark.asyncio
async def test_autogen_context_injection(e2e_client, tracked_sessions) -> None:
    memory = RemembrAutoGenMemory(client=e2e_client)
    tracked_sessions.append(memory.session_id)

    memory.save_context({"message": "Customer timezone is UTC+2"}, {"response": "Acknowledged"})
    injected = memory.inject_context_into_message("Schedule tomorrow's report")

    assert "relevant memory" in injected.lower()
    assert "utc+2" in injected.lower()


@pytest.mark.asyncio
async def test_llamaindex_retrieval(e2e_client, tracked_sessions) -> None:
    semantic = RemembrSemanticMemory.from_client(e2e_client)
    tracked_sessions.append(semantic.session_id)

    semantic.save_context({"input": "Remember that project Orion ships in May."}, {"output": "Stored."})
    docs = semantic.as_retriever().retrieve("When does project Orion ship?")

    assert docs
    assert any("orion" in doc["text"].lower() for doc in docs)


@pytest.mark.asyncio
async def test_pydantic_ai_tools(e2e_client, tracked_sessions) -> None:
    session = await e2e_client.create_session(metadata={"source": "e2e-pydantic-tools", "run_id": str(uuid.uuid4())})
    tracked_sessions.append(session.session_id)

    await e2e_client.store(content="User likes short bulleted summaries.", role="user", session_id=session.session_id)

    class Ctx:
        def __init__(self, deps):
            self.deps = deps

    ctx = Ctx(RemembrMemoryDep(client=e2e_client, session_id=session.session_id))
    result = PydanticTools.search_memory(ctx, "bulleted summaries")

    assert "relevant memories" in result.lower()
    assert "bulleted summaries" in result.lower()


@pytest.mark.asyncio
async def test_openai_agents_hooks(e2e_client, tracked_sessions) -> None:
    session = await e2e_client.create_session(metadata={"source": "e2e-openai-hooks", "run_id": str(uuid.uuid4())})
    tracked_sessions.append(session.session_id)

    RemembrMemoryTools.configure(e2e_client)
    hooks = RemembrAgentHooks(client=e2e_client, session_id=session.session_id)

    class Agent:
        name = "hook-agent"

    class Tool:
        name = "calculator"

    hooks.on_tool_end(context=None, agent=Agent(), tool=Tool(), result="42")
    time.sleep(0.5)

    results = await e2e_client.search(query="Tool completed: calculator", session_id=session.session_id, limit=5)
    assert any("tool completed" in item.content.lower() for item in results.results)


@pytest.mark.asyncio
async def test_haystack_pipeline(e2e_client, tracked_sessions) -> None:
    session = await e2e_client.create_session(metadata={"source": "e2e-haystack", "run_id": str(uuid.uuid4())})
    tracked_sessions.append(session.session_id)

    writer = RemembrMemoryWriter(client=e2e_client, default_session_id=session.session_id)
    retriever = RemembrMemoryRetriever(client=e2e_client, default_session_id=session.session_id)
    convo = RemembrConversationMemory(client=e2e_client, session_id=session.session_id, retrieval_query="incident")

    write_result = writer.run("Incident protocol: page on-call immediately", role="user")
    retrieved = retriever.run("on-call immediately")
    convo.write_messages([{"role": "assistant", "content": "incident protocol acknowledged"}])
    convo_hits = convo.retrieve(limit=5)

    assert write_result["stored"] is True
    assert any("on-call" in item.lower() for item in retrieved["memories"])
    assert len(convo_hits) >= 1
