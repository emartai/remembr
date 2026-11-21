# Remembr

Remembr is a self-hosted, open-source memory layer for AI agents. One agent can save a project decision, another can correct it, and both can retrieve the latest version with its source and authenticated author. The default Docker setup uses local Ollama embeddings for retrieval. Remembr needs no external inference API key in this setup. Each agent uses its own configured model for reasoning.

Remembr 0.2.2 is available on [GitHub](https://github.com/emartai/remembr/releases/tag/v0.2.2), [PyPI](https://pypi.org/project/remembr/0.2.2/) and [npm](https://www.npmjs.com/package/@remembr/sdk/v/0.2.2). Follow the [developer pilot](pilot.md).

Follow [Start using Remembr](getting-started.md) for prerequisites, account creation, private versus shared credentials, and your first agent memory. [Shared project memory](shared-project-memory.md) and the [MCP bridge](agent-connections.md) connect explicitly granted agents across runs.

## Who it is for

- Application developers building assistants, copilots, and internal tools that need memory without inventing a memory layer from scratch.
- Agent framework users working in LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, Pydantic AI, OpenAI Agents, or Haystack.
- Platform teams self-hosting AI infrastructure with clear security, auditability, and deletion controls.

## Start the local server

```bash
git clone https://github.com/emartai/remembr.git
cd remembr
python scripts/local_setup.py
python scripts/smoke_test.py
```

```python
import asyncio

from remembr import RemembrClient, TagFilter


async def main() -> None:
    async with RemembrClient(
        api_key="YOUR_API_KEY",
        base_url="http://localhost:8000/api/v1",
    ) as client:
        session = await client.create_session(metadata={"app": "demo"})

        episode = await client.store(
            "Ada prefers weekly billing summaries on Fridays.",
            role="user",
            session_id=session.session_id,
            tags=["kind:preference", "customer:ada"],
        )
        for _ in range(60):
            status = await client.arequest("GET", f"/memory/{episode.episode_id}/status")
            if status["embedding_status"] == "ready":
                break
            if status["embedding_status"] == "failed":
                raise RuntimeError("Embedding failed")
            await asyncio.sleep(2)
        else:
            raise TimeoutError("Memory processing timed out")

        results = await client.search(
            "When should billing summaries be sent?",
            session_id=session.session_id,
            tag_filters=[TagFilter(key="kind", value="preference")],
            search_mode="hybrid",
        )
        print(results.results[0].content)


asyncio.run(main())
```

## Core ideas

- Sessions group a conversation or workflow run.
- Episodes are immutable memory entries.
- Search can be `semantic`, `keyword`, or `hybrid`.
- Embeddings are asynchronous, so freshly stored episodes may return `embedding_status="pending"` before they become searchable semantically.
- Deletes are soft by default so teams can restore by mistake window, audit, and purge later.

## Start here

- [Framework quickstarts](quickstart/langchain.md)
- [Concepts](concepts/sessions.md)
- [API reference](api-reference.md)
- [Docker deployment](deployment/docker.md)
- [LangGraph multi-agent cookbook](cookbook/multi-agent-shared-memory.md)
