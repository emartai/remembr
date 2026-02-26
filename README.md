<div align="center">

<img src="./docs/images/logo.png" alt="Remembr Logo" width="400"/>

# Remembr

**Persistent Memory Infrastructure for AI Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)

[Quick Start](#quick-start) • [Framework Adapters](#framework-adapters) • [Self-Hosting](#self-hosting) • [Architecture](#architecture) • [Contributing](#contributing)

</div>

---

## What is Remembr?

Remembr gives AI agents persistent, searchable memory across sessions. Store, search, and retrieve conversation history using semantic search powered by vector embeddings. It supports multi-tenant isolation out of the box, so each user, agent, and session stays scoped and secure. Self-host in minutes with Docker or deploy to any cloud.

---

## Why Remembr?

- **Stateless agents forget everything** — Remembr gives them long-term memory that persists across restarts and deployments
- **Lost context kills user experience** — agents recall past interactions so users never repeat themselves
- **No cross-session memory** — Remembr links memory across sessions so agents build a complete picture over time
- **No multi-tenant isolation** — built-in org → team → user → agent → session scoping keeps data secure and separated
- **No GDPR compliance** — targeted deletion APIs let you erase user data on demand for right-to-erasure compliance

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/emartai/remembr.git
cd remembr

# 2. Configure environment
cp .env.example .env
# Edit .env — set JINA_API_KEY and generate SECRET_KEY:
# python -c "import secrets; print(secrets.token_hex(32))"

# 3. Start services
docker-compose up -d

# 4. Run migrations
docker-compose exec server alembic upgrade head

# 5. Verify
curl http://localhost:8000/health
```

See [QUICKSTART.md](QUICKSTART.md) for the full walkthrough including user registration and API key setup.

---

## Install the SDK

**Python:**

```bash
pip install remembr
```

**TypeScript:**

```bash
npm install @remembr/sdk
```

### Python Example

```python
import asyncio
from remembr import RemembrClient

async def main():
    client = RemembrClient(
        api_key="your-api-key",
        base_url="http://localhost:8000/api/v1"
    )

    # Create a session
    session = await client.create_session(
        metadata={"user": "demo", "context": "support"}
    )

    # Store a memory
    await client.store(
        content="User prefers email notifications on Fridays",
        role="user",
        session_id=session.session_id,
        tags=["preference", "notification"]
    )

    # Search memories
    results = await client.search(
        query="When should I send notifications?",
        session_id=session.session_id,
        limit=5,
        mode="hybrid"
    )

    for memory in results.results:
        print(f"[{memory.role}] {memory.content} (score: {memory.score:.3f})")

    await client.aclose()

asyncio.run(main())
```

### TypeScript Example

```typescript
import { RemembrClient } from '@remembr/sdk';

async function main() {
  const client = new RemembrClient({
    apiKey: process.env.REMEMBR_API_KEY!,
    baseUrl: 'http://localhost:8000/api/v1'
  });

  // Create session
  const session = await client.createSession({
    metadata: { user: 'demo', context: 'support' }
  });

  // Store memory
  await client.store({
    content: 'User prefers dark mode interface',
    role: 'user',
    sessionId: session.session_id,
    tags: ['preference', 'ui']
  });

  // Search memories
  const results = await client.search({
    query: 'What are the user UI preferences?',
    sessionId: session.session_id,
    limit: 5,
    mode: 'hybrid'
  });

  results.results.forEach(memory => {
    console.log(`[${memory.role}] ${memory.content} (score: ${memory.score})`);
  });
}

main();
```

---

## Framework Adapters

Remembr provides native adapters for 8 major AI frameworks. All adapters are **production-ready** and **fully tested**.

| Framework | Adapter | Status |
|-----------|---------|--------|
| **LangChain** | `adapters.langchain` | ✅ Tested |
| **LangGraph** | `adapters.langgraph` | ✅ Tested |
| **CrewAI** | `adapters.crewai` | ✅ Tested |
| **AutoGen** | `adapters.autogen` | ✅ Tested |
| **LlamaIndex** | `adapters.llamaindex` | ✅ Tested |
| **Pydantic AI** | `adapters.pydantic_ai` | ✅ Tested |
| **OpenAI Agents** | `adapters.openai_agents` | ✅ Tested |
| **Haystack** | `adapters.haystack` | ✅ Tested |

📚 **[View all adapter guides →](docs/adapters/)**

---

## Self-Hosting

### Option 1: Docker Compose (Recommended)

```bash
git clone https://github.com/emartai/remembr.git
cd remembr
cp .env.example .env
# Edit .env with your JINA_API_KEY and SECRET_KEY
docker-compose up -d
docker-compose exec server alembic upgrade head
```

### Option 2: Manual Setup

1. Install PostgreSQL 15+ with [pgvector](https://github.com/pgvector/pgvector)
2. Install Redis 7+
3. Clone the repo and install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r server/requirements.txt
```

4. Configure `.env` with your database, Redis, and Jina credentials
5. Run migrations and start the server:

```bash
cd server
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

📖 **[Full self-hosting guide →](QUICKSTART.md)**

---

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string (asyncpg) | ✅ | `postgresql+asyncpg://remembr:remembr@localhost:5432/remembr` |
| `REDIS_URL` | Redis connection string | ✅ | `redis://localhost:6379` |
| `JINA_API_KEY` | Jina AI API key for embeddings | ✅ | — |
| `SECRET_KEY` | JWT signing secret (hex string) | ✅ | — |
| `ENVIRONMENT` | Runtime environment | No | `development` |
| `LOG_LEVEL` | Logging level | No | `INFO` |
| `ALGORITHM` | JWT algorithm | No | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT access token lifetime | No | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | JWT refresh token lifetime | No | `7` |
| `JINA_EMBEDDING_MODEL` | Jina embedding model name | No | `jina-embeddings-v3` |
| `EMBEDDING_BATCH_SIZE` | Batch size for embedding requests | No | `100` |
| `DB_POOL_SIZE` | Database connection pool size | No | `10` |
| `DB_MAX_OVERFLOW` | Max overflow connections | No | `20` |
| `DB_POOL_TIMEOUT` | Pool connection timeout (seconds) | No | `30` |
| `DB_POOL_RECYCLE` | Connection recycle interval (seconds) | No | `1800` |
| `RATE_LIMIT_DEFAULT_PER_MINUTE` | Default rate limit | No | `100` |
| `RATE_LIMIT_SEARCH_PER_MINUTE` | Search rate limit | No | `30` |
| `SHORT_TERM_MAX_TOKENS` | Max tokens in short-term window | No | `4000` |
| `SHORT_TERM_AUTO_CHECKPOINT_THRESHOLD` | Auto-checkpoint threshold | No | `0.8` |
| `API_V1_PREFIX` | API version prefix | No | `/api/v1` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | No | `[]` |
| `SENTRY_DSN` | Sentry error tracking DSN | No | — |

---

## Architecture

```mermaid
graph TB
    subgraph "AI Frameworks"
        LC[LangChain]
        LG[LangGraph]
        CA[CrewAI]
        AG[AutoGen]
        LI[LlamaIndex]
        PA[Pydantic AI]
        OA[OpenAI Agents]
        HS[Haystack]
    end

    subgraph "Remembr Platform"
        subgraph "SDK Layer"
            PY[Python SDK]
            TS[TypeScript SDK]
        end

        subgraph "API Server — FastAPI"
            AUTH[Authentication]
            MEM[Memory API]
            SESS[Sessions API]
            RATE[Rate Limiting]
        end

        subgraph "Storage"
            PG["PostgreSQL + pgvector
            Long-term episodic memory"]
            REDIS["Redis
            Short-term cache"]
        end

        JINA["Jina AI
        Embeddings"]
    end

    LC --> PY
    LG --> PY
    CA --> PY
    AG --> PY
    LI --> PY
    PA --> PY
    OA --> PY
    HS --> PY

    PY --> AUTH
    TS --> AUTH
    AUTH --> MEM
    AUTH --> SESS
    AUTH --> RATE
    MEM --> PG
    MEM --> REDIS
    MEM --> JINA
    SESS --> REDIS
```

Remembr is built on a **FastAPI** server backed by **PostgreSQL with pgvector** for long-term episodic memory storage and semantic vector search, **Redis** for short-term conversation window caching and rate limiting, and **Jina AI** for generating high-quality text embeddings. The system uses multi-tenant row-level security (RLS) to isolate data across organizations, teams, users, agents, and sessions. Authentication is handled via JWT tokens with refresh support, and the entire stack can be self-hosted with Docker Compose or deployed to any cloud platform.

---

## Repository Structure

```
remembr/
├── adapters/              # Framework adapters (8 frameworks)
│   ├── langchain/
│   ├── langgraph/
│   ├── crewai/
│   ├── autogen/
│   ├── llamaindex/
│   ├── pydantic_ai/
│   ├── openai_agents/
│   └── haystack/
├── server/                # FastAPI server
│   ├── app/               # Application code
│   │   ├── api/           # REST endpoints
│   │   ├── db/            # Database models & connection
│   │   ├── services/      # Business logic
│   │   ├── repositories/  # Data access layer
│   │   └── middleware/     # Auth, rate limiting
│   ├── alembic/           # Database migrations
│   └── tests/             # Server unit & integration tests
├── sdk/                   # Client SDKs
│   ├── python/            # Python SDK (PyPI: remembr)
│   └── typescript/        # TypeScript SDK (npm: @remembr/sdk)
├── docs/                  # Documentation
│   ├── adapters/          # Adapter-specific guides
│   ├── api-reference.md   # REST API reference
│   └── images/            # Logo and diagrams
├── tests/                 # End-to-end & integration tests
├── docker-compose.yml     # Local development stack
├── .env.example           # Environment template
├── QUICKSTART.md          # Self-hosted setup guide
├── CONTRIBUTING.md        # Contribution guidelines
└── LICENSE                # MIT License
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Branching strategy and commit conventions
- Testing guidelines
- Pull request process

---

## License

MIT License — Copyright (c) 2026 [Emmanuel Nwanguma](https://linkedin.com/in/nwangumaemmanuel)

See [LICENSE](LICENSE) for full text.
