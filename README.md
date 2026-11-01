# Remembr

[![CI](https://github.com/emartai/remembr/actions/workflows/ci.yml/badge.svg)](https://github.com/emartai/remembr/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/remembr)](https://pypi.org/project/remembr/)
[![npm version](https://img.shields.io/npm/v/@remembr/sdk)](https://www.npmjs.com/package/@remembr/sdk)
[![License](https://img.shields.io/github/license/emartai/remembr)](LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/remembr)](https://pypi.org/project/remembr/)

Remembr gives AI agents durable, searchable memory with a `store`, `search`, and `delete` workflow, session-aware context, and a self-hosted stack with local embeddings.

## Quick Start

```bash
git clone https://github.com/emartai/remembr.git
cd remembr
python scripts/local_setup.py
python scripts/smoke_test.py
```

Requires Python 3.11+, Docker Compose v2, a running Linux container engine, and internet access for the initial images, dependencies and model download. Setup creates `.env` if needed, generates a signing secret, and starts PostgreSQL, Redis, PgBouncer, Ollama, migrations, the API and workers. Existing secrets and data are retained. The smoke test creates local test accounts and verifies queued embeddings, retrieval, access isolation and deletion.

`EMBEDDING_PROVIDER=ollama` is the Docker default; `sentence_transformers` is the bare Python default and needs its optional dependency installed. No external inference API key is required for either local provider. `/health` checks HTTP liveness; `/ready` checks the memory pipeline and performs a short embedding request.

See [QUICKSTART.md](QUICKSTART.md) for the full self-hosted walkthrough.

See [Verified environment](docs/compatibility.md) for tested SDK/framework versions and the scope of local verification.

## Shared project memory (local development)

Separate agent credentials can share explicitly granted project spaces. Existing private episodes
stay private. See [shared project memory](docs/shared-project-memory.md) for permissions, authorship,
corrections, expiry and retrieval budgets, and [agent connections](docs/agent-connections.md) for the
local MCP bridge and LangGraph/Claude Code/Codex setup. Open `/explorer` on your running server to
browse and manage permitted memory. These additions are in the local source and are not yet published.

## Install The SDKs

```bash
pip install remembr
npm install @remembr/sdk
```

## Python Example

```python
import asyncio

from remembr import RemembrClient


async def main() -> None:
    async with RemembrClient(
        api_key="your-api-key",
        base_url="http://localhost:8000/api/v1",
    ) as client:
        session = await client.create_session(
            metadata={"user": "demo", "context": "support"}
        )

        episode = await client.store(
            content="User prefers email notifications on Fridays",
            role="user",
            session_id=session.session_id,
            tags=["preference", "notification"],
        )

        for _ in range(60):
            status = await client.arequest("GET", f"/memory/{episode.episode_id}/status")
            if status["embedding_status"] == "ready":
                break
            if status["embedding_status"] == "failed":
                raise RuntimeError("Embedding failed; inspect worker logs")
            await asyncio.sleep(1)
        else:
            raise TimeoutError("Embedding did not become ready")

        results = await client.search(
            query="When should I send notifications?",
            session_id=session.session_id,
            limit=5,
            search_mode="hybrid",
            weights={"semantic": 0.6, "keyword": 0.3, "recency": 0.1},
        )

        for memory in results.results:
            print(f"[{memory.role}] {memory.content} (score: {memory.score:.3f})")


asyncio.run(main())
```

## TypeScript Example

```typescript
import { RemembrClient } from '@remembr/sdk';

async function main() {
  const client = new RemembrClient({
    apiKey: process.env.REMEMBR_API_KEY!,
    baseUrl: 'http://localhost:8000/api/v1'
  });

  const session = await client.createSession({
    user: 'demo',
    context: 'support'
  });

  const episode = await client.store({
    content: 'User prefers dark mode interface',
    role: 'user',
    sessionId: session.session_id,
    tags: ['preference', 'ui']
  });

  const deadline = Date.now() + 60_000;
  while (true) {
    const response = await fetch(
      `http://localhost:8000/api/v1/memory/${episode.episode_id}/status`,
      { headers: { 'X-API-Key': process.env.REMEMBR_API_KEY! } }
    );
    if (!response.ok) throw new Error(`Status check failed: ${response.status}`);
    const { data } = await response.json();
    if (data.embedding_status === 'ready') break;
    if (data.embedding_status === 'failed') throw new Error('Embedding failed');
    if (Date.now() >= deadline) throw new Error('Embedding processing timed out');
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  const results = await client.search({
    query: 'What are the user UI preferences?',
    sessionId: session.session_id,
    limit: 5,
    searchMode: 'hybrid',
    weights: { semantic: 0.6, keyword: 0.3, recency: 0.1 }
  });

  results.results.forEach((memory) => {
    console.log(`[${memory.role}] ${memory.content} (score: ${memory.score})`);
  });
}

main();
```

## Environment Variables

| Variable | Purpose | Required | Default |
| --- | --- | --- | --- |
| `DATABASE_URL` | PostgreSQL connection string | Yes | `postgresql://postgres:postgres@localhost:5432/remembr` |
| `REDIS_URL` | Redis connection string | Yes | `redis://localhost:6379` |
| `SECRET_KEY` | JWT signing secret | Yes | None |
| `EMBEDDING_PROVIDER` | Embedding backend: `sentence_transformers`, `jina`, `ollama`, or `openai` | Yes | `sentence_transformers` |
| `SENTENCE_TRANSFORMERS_MODEL` | Local sentence-transformers model name | No | `all-MiniLM-L6-v2` |
| `JINA_API_KEY` | Jina API key when `EMBEDDING_PROVIDER=jina` | No | None |
| `JINA_EMBEDDING_MODEL` | Jina embedding model | No | `jina-embeddings-v3` |
| `OLLAMA_BASE_URL` | Ollama base URL when `EMBEDDING_PROVIDER=ollama` | No | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | Ollama embedding model | No | `nomic-embed-text` |
| `OPENAI_API_KEY` | OpenAI API key when `EMBEDDING_PROVIDER=openai` | No | None |
| `OPENAI_EMBEDDING_MODEL` | OpenAI embedding model | No | `text-embedding-3-small` |
| `OTEL_ENABLED` | Enable OpenTelemetry export | No | `false` |
| `OTEL_EXPORTER_ENDPOINT` | OTLP exporter endpoint | No | None |

## Docs

Full documentation: **https://emartai.github.io/remembr/**

- [Framework quickstarts](https://emartai.github.io/remembr/docs/quickstart/langchain)
- [API reference](https://emartai.github.io/remembr/docs/api-reference)
- [Self-hosting guide](https://emartai.github.io/remembr/docs/self-hosted)
- [Python SDK README](sdk/python/README.md)
- [TypeScript SDK README](sdk/typescript/README.md)
