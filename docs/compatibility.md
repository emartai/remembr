# Verified environment

See the public [verification record](verification.md) for acceptance results and limits. Company-workspace paths below identify private maintainer records and are not required to use Remembr.

Local verification on 29 October 2026 used the following versions. These are observed test environments, not a certification of every version allowed by dependency ranges.

| Component | Verified environment | Evidence |
| --- | --- | --- |
| Python SDK candidate 0.2.1 | Python 3.11.9; HTTPX 0.28.1 | 54 tests; installed-wheel HTTP and authentication probes |
| TypeScript SDK candidate 0.2.1 | Node.js 22.21.1 | Build/type check; 20 tests; packed-package HTTP probes |
| LangGraph adapter | LangGraph 1.2.14; Python 3.11.9 | One real HTTP/event-loop regression |
| Database and API regression suite | Python 3.11.9 against PostgreSQL 16 with pgvector | 77 selected tests, including real filters, scope boundaries, idempotency and non-superuser RLS |
| Local embedding runtime | Existing Windows Ollama service; publisher Nomic Embed Text v1.5 F16 GGUF | SHA-256-verified model; valid, nonzero 768-dimensional embeddings; live API/worker lifecycle |

The local embedding tag is `nomic-embed-text:publisher-f16`, configured explicitly in the development `.env`. Public defaults remain `nomic-embed-text` with the bundled Ollama service. The publisher model and registry package have distinct packaging; retrieval-quality and long-context equivalence have not been benchmarked.

The Docker API and worker were tested with local host Ollama through `host.docker.internal`. The bundled Ollama image/model-download path did not complete on this network. Jina, OpenAI and sentence-transformers have provider unit tests; live inference with those providers was not verified in this run.

Shared project memory adds Python/TypeScript project APIs and an optional stdio MCP bridge using the official Python MCP SDK (tested with 1.30.0). On 31 October 2026, the combined handoff passed: a real LangGraph 1.2.14 StateGraph process wrote a finding, Claude Code 2.1.296 retrieved and corrected it through MCP, the API and worker containers were recreated, and Codex CLI 0.166.0-alpha.5.1 retrieved both revisions and their authenticated authors through MCP. Three distinct credentials were used; read-only writes, grant removal and revocation were verified. This tested SDK source through `PYTHONPATH`, not a newly published package. The company workspace record is `openpeople/workspace/research/remembr-runtime-2026-10-31/REPORT.md`.

Existing framework adapters continue to use the legacy private-memory API. Use the new project SDK or MCP bridge for shared spaces. Full framework compatibility matrices and durable framework resume remain unverified; context-memory sharing does not establish durable graph checkpoint recovery.

Explorer acceptance on 1 November 2026 passed 19 real Chromium browser checks using Playwright 1.64.1 and Chromium 151.0.7922.34: login, selection, real local search, lifecycle operations, permission changes, disconnect handling and responsive layouts at 320/390 px. Pending/failed rendering and service-error cases used controlled browser responses; semantic retrieval, expiry, corrections, deletion and grants used the live API. Twelve PostgreSQL/explorer regressions and the TypeScript build also passed. The record is `openpeople/workspace/research/remembr-explorer-2026-11-01/REPORT.md` in the company workspace. This does not establish Firefox/WebKit or physical-device compatibility.

The Windows test suite emitted asyncpg teardown/deprecation warnings. See the local release verification record for logs; the selected tests completed successfully. Bare-process Celery connection-pool behavior and production deployment guarantees remain outside this Docker verification.

See [Local setup](local-setup.md) for the verified startup flow and configuration requirements.

Clean-install/package acceptance on 1 November 2026 used a new source copy, empty PostgreSQL/Redis volumes, migrations 001–009, canonical Docker images and a separately downloaded native Ollama `nomic-embed-text` model. Installed Python 0.2.1 wheel/sdist, npm 0.2.1 CommonJS/ESM and the installed MCP console passed live workflows; the quickstart smoke also passed. Windows consumers used Python 3.11.9 and Node 22.21.1. The fresh Linux API used Python 3.11.18, FastAPI 0.162.0, SQLAlchemy 2.1.6, asyncpg 0.32.0, Redis client 6.4.0, Celery 5.6.3 and tiktoken 0.14.0. Full environment and archive hashes are in `openpeople/workspace/research/remembr-clean-install-2026-11-01/REPORT.md` in the company workspace. The bundled Ollama image download remained unverified after premature EOF; the test build required temporary host-resolved DNS entries. Python 0.2.1 is now published on PyPI and the server source is tagged v0.2.1. npm 0.2.1 publication remains pending; use its source archive for the new project APIs.
