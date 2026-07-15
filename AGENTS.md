<!-- mindr-generated -->

# remembr

**Repository:** https://github.com/emartai/remembr

## Commands

| Task | Command |
|------|---------|
| Install | `make setup` |

## Stack & Architecture

**Language**
- Python — language
- TypeScript — language

**Framework**
- FastAPI — web framework
- LangChain — LLM framework
- LlamaIndex — LLM framework
- React — UI library

**Database**
- Alembic — DB migrations
- pgvector — vector search
- PostgreSQL — database driver
- Redis — cache / pub-sub
- SQLAlchemy — ORM

**Testing**
- Jest — test runner

**Tooling**
- Celery — task queue
- HTTPX — HTTP client
- OpenAI — LLM client
- Pydantic — data validation
- Pydantic Settings — config management
- Sentence Transformers — text embeddings
- Uvicorn — ASGI server

## Conventions

### Javascript

| Category | Style | Confidence | Samples |
|----------|-------|-----------|---------|
| Variable names | `lowercase` | 86% | 158 |
| File names | `lowercase` | 83% | 6 |
| Function names | `camelCase` | 77% | 22 |
### Python

| Category | Style | Confidence | Samples |
|----------|-------|-----------|---------|
| Class / type names | `PascalCase` | 100% | 218 |
| Test file pattern | `tests/` | 100% | 85 |
| errorHandling | `specific-except` | 100% | 120 |
| Function names | `snake_case` | 73% | 1308 |
| File names | `snake_case` | 49% | 221 |
### Typescript

| Category | Style | Confidence | Samples |
|----------|-------|-----------|---------|
| Class / type names | `PascalCase` | 100% | 8 |
| Test file pattern | `tests/` | 100% | 4 |
| errorHandling | `untyped-catch` | 100% | 5 |
| File names | `lowercase` | 86% | 14 |
| Variable names | `lowercase` | 77% | 156 |

## Recent Decisions

- **2026-07-12** — refactor: migrate memory layer to new architecture *(keyword)*
- **2026-07-12** — remembr uses pgvector for episodic long-term memory

## Active Warnings

### Technical Debt

- `server/app/main.py:undefined` — example debt for dogfood test
