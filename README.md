# Remembr

[![CI](https://github.com/yourusername/remembr/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/remembr/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/yourusername/remembr/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/remembr)

Persistent memory infrastructure for AI agents.

## Overview

Remembr provides a unified memory layer for AI agents across multiple frameworks. It consists of:

- **Server**: FastAPI-based memory service with PostgreSQL backend
- **SDKs**: Python and TypeScript clients for interacting with the memory service
- **Adapters**: Framework-specific integrations for LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, Pydantic AI, OpenAI Agents, and Haystack

## Architecture

```
remembr/
├── server/          # FastAPI memory service
├── sdk/
│   ├── python/      # Python SDK
│   └── typescript/  # TypeScript SDK
└── adapters/        # Framework-specific adapters
    ├── langchain/
    ├── langgraph/
    ├── crewai/
    ├── autogen/
    ├── llamaindex/
    ├── pydantic_ai/
    ├── openai_agents/
    └── haystack/
```

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+ (with pgvector extension)
- Redis (or Upstash account)

### Quick Start

1. Copy environment configuration:
```bash
cp .env.example .env
```

2. Edit `.env` and set required variables:
   - `DATABASE_URL`: PostgreSQL connection string
   - `REDIS_URL`: Redis connection string
   - `SECRET_KEY`: Generate with `openssl rand -hex 32`
   - `JINA_API_KEY`: Get from https://jina.ai/

3. Install dependencies:
```bash
make setup
```

Or manually:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Server setup
cd server
pip install -e ".[dev]"

# Python SDK setup
cd ../sdk/python
pip install -e ".[dev]"

# TypeScript SDK setup
cd ../typescript
npm install
```

## Development

### Running the Server

```bash
cd server
uvicorn app.main:app --reload
```

### Running Tests

```bash
# Python tests
cd server
pytest tests/ -v --cov=app

# TypeScript tests
cd sdk/typescript
npm test

# E2E tests
cd tests/e2e
pytest
```

### Linting

```bash
# Run pre-commit on all files
pre-commit run --all-files

# Or manually
ruff check server/app --fix
ruff format server/app
```

## Deployment

### Quick Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

See [RAILWAY_QUICKSTART.md](./RAILWAY_QUICKSTART.md) for a 5-minute setup guide.

### Full Deployment Guide

See [DEPLOYMENT.md](./DEPLOYMENT.md) for comprehensive deployment instructions including:
- Railway configuration
- Supabase (PostgreSQL + pgvector) setup
- Upstash (Redis) setup
- Environment variables
- Staging vs Production setup
- Database migrations
- Monitoring and scaling

## CI/CD

GitHub Actions automatically runs on every push and pull request:
- Linting with ruff
- Tests with pytest
- Coverage reporting (minimum 70%)

See [.github/workflows/README.md](./.github/workflows/README.md) for details.

## License

MIT
