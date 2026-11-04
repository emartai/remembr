# Local setup and release checks

This walkthrough uses the source checkout and local Ollama embeddings. It does not require an additional LLM or a paid inference account.

## Requirements

- Python 3.11 or later.
- Docker with Compose v2 and a working Linux container engine. On Windows, start Docker Desktop first.
- Internet access for initial container images, Python dependencies and the embedding model. Local inference can run without an external provider once these downloads are available.
- Available host ports: API 8000, PostgreSQL 5432, PgBouncer 6432, Redis 6379 and Ollama 11434. Services bind to loopback by default.

## Start and verify

From the repository root:

```sh
python scripts/local_setup.py
python scripts/smoke_test.py
```

On macOS/Linux use `python3` if needed. Shell wrappers are also available: `bash scripts/docker-init.sh` or `powershell -File scripts/docker-init.ps1`.

Setup creates `.env` from `.env.example` only when missing and replaces an empty/example signing secret with a random value. Existing credentials are not printed. Keep `.env` out of version control.

The startup order is:

1. Check Docker and validate Compose configuration.
2. Start PostgreSQL, Redis and PgBouncer first so storage/port failures are reported before downloading the inference image.
3. Start Ollama, pull the configured `OLLAMA_EMBEDDING_MODEL` (default `nomic-embed-text`), build the application and complete migrations before API and worker startup. First-time downloads/builds have a one-hour command deadline.
4. Wait for database/migration, Redis, worker and embedding checks to succeed.

The smoke test registers two temporary organizations, creates a session, stores a uniquely identifiable episode and polls its processing status with a deadline. It verifies the exact episode in semantic, keyword and hybrid searches, rejects access/deletion from the other organization, deletes the episode and verifies it no longer appears. Test accounts and session metadata remain; run this on a development instance.

No SDK packages or images are published by these commands.

## Readiness and processing

### Use an existing local Ollama installation

If Ollama already runs on the Docker host, install `nomic-embed-text` there with `ollama pull nomic-embed-text`, then set `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env` on Docker Desktop. Setup recognizes this external endpoint and skips the bundled inference container. The explicit `--skip-ollama-bootstrap` option is also available. Readiness still requires a real embedding response. Keep the host Ollama service running while using Remembr. Docker Desktop must be able to reach that host endpoint. The API, database and worker still run in Docker. For an imported model, set `OLLAMA_EMBEDDING_MODEL` to its exact local tag.

```sh
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/ready
docker compose ps -a
docker compose logs --tail 100 server worker migrate
```

`/health` is a liveness endpoint and can return 200 while dependencies are unavailable. `/ready` returns 200 only when the database has current migrations and pgvector, Redis responds, a Celery worker has the embedding task registered, and the embedding provider produces a valid vector. Otherwise it returns 503 with component status. Database, Redis and worker checks have ten-second deadlines; embedding inference has 30 seconds to accommodate cold CPU initialization. The embedding check invokes the configured provider; with a paid provider it can incur usage charges.

The Docker build downloads and caches the session tokenizer in the image. First writes and container recreation then use that local asset.

For an authenticated episode, `GET /api/v1/memory/{episode_id}/status` returns `pending`, `ready` or `failed`. A successful store does not mean the episode is already semantically searchable. Wait for `ready`, handle `failed`, and enforce a deadline rather than using a fixed sleep.

The episode is committed before its task is published so a fast worker can read it. If queue publication fails, storage still succeeds and its embedding status is `failed`; the raw episode is retained. There is no durable queue outbox or automatic recovery of these failed publications yet. Worker inference failures are retried separately.

## Configuration and restarting

PostgreSQL and Redis use named data volumes. Redis has append-only persistence with a one-second fsync interval, retaining broker queues and session context across clean container recreation. An abrupt machine/power failure can still lose roughly the last second of Redis writes; this is not a durable database outbox. Existing installations need to preserve their old Redis data when adopting the new named volume rather than starting an empty volume over it.

Change host ports using `REMEMBR_PORT`, `POSTGRES_PORT`, `PGBOUNCER_PORT`, `REDIS_PORT` or `OLLAMA_PORT` in `.env`. Internal service URLs keep their container ports. If the API host port changes, pass the matching URL to the smoke test:

```sh
python scripts/smoke_test.py --url http://localhost:8001
```

For a second installation, also set a distinct `COMPOSE_PROJECT_NAME` before starting it. Container names and named volumes are scoped to that project. Assign unused host ports to every published service; changing the project name alone does not change port bindings. The usual checkout named `remembr` retains the default `remembr-*` container names.

`docker compose up -d` restarts the core services. To explicitly start the bundled Ollama services too, use `docker compose --profile ollama up -d`. Re-running the setup script is supported and retains volumes. `docker compose --profile ollama down` stops the local stack without deleting volumes.

This Compose setup targets the bundled local database. An external database requires an explicit migration configuration as well as the API and worker connection settings.

Switching embedding models can change dimensions and search compatibility. Do not switch a populated instance without a re-embedding/migration plan. Changing `EMBEDDING_PROVIDER` alone does not install optional dependencies: `sentence_transformers` and `openai` require a suitably built server image or a bare Python installation with those packages.

## Troubleshooting

- Docker unavailable or timed out: check `docker info`; on Windows confirm Docker Desktop's Linux engine is ready. Setup exits without claiming success.
- Fresh image builds use Python's standard-library HTTP probe for API health; installing an OS-level `curl` package is unnecessary. Internet access is still required for Python dependencies and tokenizer assets unless those build layers are cached.
- If package downloads fail inside Docker but host DNS resolves the same domains, diagnose Docker's build networking separately from SDK packaging. The clean-install verification used temporary build-only `extra_hosts` entries resolved on the host for `pypi.org`, `files.pythonhosted.org` and the tokenizer asset host. No global DNS or TLS-verification settings were changed. These are environment-specific diagnostics, not fixed IP addresses to commit to deployments.
- If the Windows `docker compose` wrapper hangs but the installed Compose binary works, set `DOCKER_COMPOSE_EXE` to that executable's full path in `.env` (single-quote paths containing spaces). Setup can then invoke it directly. `COMPOSE_BAKE=false` can be set in the calling environment to use Compose's ordinary build path when Bake hangs.
- Migration failure: inspect `docker compose logs migrate`. API and workers wait until migration succeeds.
- Ollama/model failure: inspect `docker compose --profile ollama logs ollama` and rerun setup. The model pull must finish successfully.
- Memory stays pending: inspect worker health, Redis connectivity and worker logs. Do not treat an empty search result as proof that storage failed.
- Readiness shows embeddings unhealthy: the first model load can be slow; retry after it warms. Check the configured model and provider dependencies.

### Windows recovery checks

Check current state with `docker ps -a`; a successful check from an earlier session does not mean the containers are still running. Resume the configured stack with `docker compose up -d --no-build`, retaining its volumes. If configured to use native Windows Ollama through `host.docker.internal`, start that service too; the core Compose services do not start the native process. Do not enable a second Ollama service on the same host port.

Verify `/api/v1/ready` after startup. It must report the database, Redis, worker and embeddings healthy. A responding worker must register both private-memory and shared-project embedding tasks. `/api/v1/health` alone does not establish that embeddings can be processed. Check a real memory's processing status and semantic recall when diagnosing a stalled queue.

On a small Windows host, Docker, local models and coding clients share physical memory. Inspect `docker stats --no-stream` and available host memory before attributing health-probe process startup timeouts to an API error. Compare ordinary health latency with full readiness, worker logs and Docker's health history. Preserve the configured model when resuming a populated database.

A socket-access or Docker named-pipe permission error from a restricted coding environment is a tooling access failure. Run authorized diagnostics through that environment's approval mechanism; do not change product grants or disable checks to make a diagnostic pass. Recreating the single local API container briefly interrupts connections; wait for readiness before resuming clients.

### Clean-install verification scope

On 1 November 2026, a copy of the current unreleased source was built with no copied `.env`, installed SDK dependencies or generated SDK outputs. A separate Compose project applied migrations 001–009 to new PostgreSQL/Redis volumes. Its API/worker images came from the canonical Dockerfile; dependency and tokenizer layers were built successfully and then shared by the remaining services. The verified inference path used native Windows Ollama with an initially empty model directory and a fresh `nomic-embed-text` download. The default bundled Ollama image download failed with premature EOF on that network, so it is not counted as verified.

Fresh consumer environments installed the Python 0.2.1 wheel with MCP, the Python source distribution without MCP, and the npm 0.2.1 archive. Installed SDK imports resolved from those environments rather than the source checkout. Live Python sync/async, TypeScript CommonJS/ESM, all four installed MCP tools, and the quickstart smoke passed. See the company workspace record `openpeople/workspace/research/remembr-clean-install-2026-11-01/REPORT.md` for artifact hashes, environment versions and limits. Python 0.2.1 is now published on PyPI; npm 0.2.1 publication remains pending. The tested server source is tagged v0.2.1.

The public [verification record](verification.md) summarizes the completed checks and their limits.

## Development checks

Run Python SDK tests from `sdk/python`, TypeScript build/tests from `sdk/typescript`, and server tests from `server`, using the commands in `AGENTS.md`. Server integration tests require a separate, disposable PostgreSQL database with pgvector; fixtures create and drop tables. Never point `TEST_DATABASE_URL` at your working memory database.

The release record should distinguish unit tests, package installation checks and a real Docker/Ollama smoke run. Passing one does not establish the others.
