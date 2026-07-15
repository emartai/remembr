<!-- mindr-generated -->

# remembr

> Repository: https://github.com/emartai/remembr

## Project Overview

This is a **project** using Python, TypeScript, FastAPI, LangChain +15 more.

## Commands

- **Install:** `make setup`

## Stack & Architecture

- **Python** — language
- **TypeScript** — language
- **FastAPI** — web framework
- **LangChain** — LLM framework
- **LlamaIndex** — LLM framework
- **React** — UI library
- **Alembic** — DB migrations
- **pgvector** — vector search
- **PostgreSQL** — database driver
- **Redis** — cache / pub-sub
- **SQLAlchemy** — ORM
- **Jest** — test runner
- **Celery** — task queue
- **HTTPX** — HTTP client
- **OpenAI** — LLM client
- **Pydantic** — data validation
- **Pydantic Settings** — config management
- **Sentence Transformers** — text embeddings
- **Uvicorn** — ASGI server

## Conventions

### Javascript

- Use all-lowercase for **Variable names** (86% consistency, 158 samples)
- Use all-lowercase for **File names** (83% consistency, 6 samples)
- Use camelCase for **Function / method names** (77% consistency, 22 samples)

### Python

- Use PascalCase for **Class / type names** (100% consistency, 218 samples)
- Use `tests/` for **Test file location** (100% consistency, 85 samples)
- Use `specific-except` for **errorHandling** (100% consistency, 120 samples)
- Use snake_case for **Function / method names** (73% consistency, 1308 samples)
- Use snake_case for **File names** (49% consistency, 221 samples)

### Typescript

- Use PascalCase for **Class / type names** (100% consistency, 8 samples)
- Use `tests/` for **Test file location** (100% consistency, 4 samples)
- Use `untyped-catch` for **errorHandling** (100% consistency, 5 samples)
- Use all-lowercase for **File names** (86% consistency, 14 samples)
- Use all-lowercase for **Variable names** (77% consistency, 156 samples)

## Recent Decisions

Context for understanding recent architectural choices:

- **2026-07-12** — refactor: migrate memory layer to new architecture *(keyword)*
- **2026-07-12** — remembr uses pgvector for episodic long-term memory

## Active Warnings

Known issues to be aware of while working on this codebase:

- `server/app/main.py:undefined` — example debt for dogfood test

## Memory

This file is maintained by **[Mindr](https://github.com/emartai/mindr)**, which observes your commits and learns your codebase conventions automatically.

```
# Search Mindr memory
mindr search "<query>"

# Refresh this file
mindr generate claude-md
```
