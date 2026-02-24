# Changelog

## v0.1.0 - MVP Release

### Added

#### Core platform
- FastAPI server with versioned API (`/api/v1`) and structured error envelopes.
- Async SQLAlchemy with PostgreSQL + pgvector support for episodic memory.
- Redis-backed short-term memory and checkpoint/restore support.
- JWT + API key authentication with request-scoped context propagation.
- Forgetting APIs for episode/session/user deletion (GDPR workflows).
- Hybrid retrieval with semantic + metadata filtering.

#### SDKs
- Python SDK for sessions, memory CRUD/search, checkpoints, and forgetting.
- TypeScript SDK with equivalent memory/session/checkpoint management APIs.

#### Adapter ecosystem (8 frameworks)
- LangChain adapter
- LangGraph adapter (including checkpointer)
- CrewAI adapter
- AutoGen adapter
- LlamaIndex adapter
- Pydantic AI adapter
- OpenAI Agents SDK adapter
- Haystack adapter

#### Production hardening
- Redis-backed API rate limiting with endpoint-specific limits.
- Tuned database connection pooling and timeout visibility.
- Security checklist documentation and auth coverage tests.
- Performance baseline tooling with Locust load scenario.

### Documentation
- Quickstart guide (Python + TypeScript).
- Full API reference.
- Concepts guide (scoping, memory layers, hybrid search, forgetting).
- Self-hosted setup guide.
- Adapter-specific usage guides for all eight frameworks.
