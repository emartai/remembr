# Remembr — Self-Hosted Quick Start

Get Remembr running locally in under 10 minutes.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| **Docker** & **Docker Compose** | v20+ / v2+ |
| **Python** | 3.11+ |
| **Jina AI API Key** | Free at [jina.ai](https://jina.ai) |

---

## 1. Clone the Repository

```bash
git clone https://github.com/emartai/remembr.git
cd remembr
```

## 2. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and set the following values:

```bash
# Required — get a free key at https://jina.ai
JINA_API_KEY=your-jina-api-key-here

# Required — generate a secret key for JWT authentication
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
```

All other defaults (database URL, Redis URL, etc.) are pre-configured for the Docker Compose setup.

## 3. Start Services with Docker Compose

```bash
docker-compose up -d
```

This starts three services:

| Service | Port | Description |
|---------|------|-------------|
| **PostgreSQL** (pgvector) | 5432 | Long-term episodic memory storage |
| **Redis** | 6379 | Short-term memory cache |
| **Remembr Server** | 8000 | FastAPI REST API |

## 4. Run Database Migrations

```bash
docker-compose exec server alembic upgrade head
```

## 5. Verify with Health Check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "environment": "development",
  "version": "0.1.0"
}
```

## 6. Register Your First User and Get an API Key

**Register:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-secure-password",
    "name": "Your Name"
  }'
```

**Login to get a JWT token:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "you@example.com",
    "password": "your-secure-password"
  }'
```

Save the `access_token` from the response.

**Create an API key:**

```bash
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "Authorization: Bearer <your-access-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-first-key", "scope": "agent"}'
```

Save the returned API key — you'll use it with the SDK.

## 7. First Memory Store and Search

**Install the Python SDK:**

```bash
pip install remembr
```

**Store and search a memory:**

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
        metadata={"user": "demo", "context": "quickstart"}
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

---

## Stopping Services

```bash
docker-compose down
```

To also remove the database volume:

```bash
docker-compose down -v
```

---

## Next Steps

- Read the [README](README.md) for full documentation
- Explore the [API Reference](docs/api-reference.md)
- Try [framework adapters](adapters/) for LangChain, CrewAI, and more
- See [CONTRIBUTING.md](CONTRIBUTING.md) to get involved

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **Health check fails** | Ensure all containers are running: `docker-compose ps` |
| **Database connection error** | Wait 10-15s for PostgreSQL to initialize, then retry |
| **Embedding errors** | Verify `JINA_API_KEY` is set correctly in `.env` |
| **Port conflicts** | Change ports in `docker-compose.yml` if 5432, 6379, or 8000 are in use |
