# Remembr local quickstart

Run these commands from a source checkout with Python 3.11+, Docker Compose v2 and a running Linux container engine:

```sh
git clone https://github.com/emartai/remembr.git
cd remembr
python scripts/local_setup.py
python scripts/smoke_test.py
```

Use `python3` on systems where that is the Python executable. Initial setup downloads images, dependencies and the local embedding model, so internet access is needed. Setup creates `.env`, generates a signing secret and retains existing data and configured secrets.

The smoke test creates local test accounts, waits for the exact episode's embedding, checks retrieval and tenant isolation, and verifies deletion. It exits with an error if processing fails or exceeds its deadline. Accounts and session metadata remain in the development instance.

- API: `http://localhost:8000/api/v1`
- API documentation: `http://localhost:8000/docs`
- Liveness: `http://localhost:8000/api/v1/health`
- Pipeline readiness: `http://localhost:8000/api/v1/ready`

Read [Local setup and release checks](docs/local-setup.md) for startup order, configuration, status polling, provider options and troubleshooting.

## Use an SDK

Install from this checkout when testing unreleased changes:

```sh
python -m pip install ./sdk/python
# Include the optional MCP bridge when connecting MCP-capable agents:
python -m pip install './sdk/python[mcp]'
cd sdk/typescript
npm ci
npm run build
npm pack
```

The npm command creates a local package archive; install it into your application with `npm install /path/to/remembr-sdk-0.2.1.tgz`. These commands do not publish packages.

Register through `POST /api/v1/auth/register` with `email`, `password` and `org_name`. Use the returned access token as a bearer token for `POST /api/v1/api-keys` with a `name`. Supply the resulting API key to the SDK. The [smoke test](scripts/smoke_test.py) contains an executable example of this sequence without printing credentials.

See the [Python SDK](sdk/python/README.md), [TypeScript SDK](sdk/typescript/README.md) and [API reference](docs/api-reference.md). Memory writes return before background processing completes: poll `GET /api/v1/memory/{episode_id}/status` with your API key until `ready` before expecting semantic retrieval; handle `failed` and impose a timeout.

The key flow above is for private/session memory. For shared project memory, create a project and space, issue a separate `rmsp_` credential per agent, and grant access to that space. Use `client.projects` in either SDK or the optional `remembr-mcp` console entry point. See [shared project memory](docs/shared-project-memory.md) and [agent connections](docs/agent-connections.md). A built wheel can be installed with its MCP extra using `python -m pip install '/path/to/remembr-0.2.1-py3-none-any.whl[mcp]'`.

## Native Ollama alternative

For an existing native Ollama installation, start its service and wait for its local `/api/tags` endpoint to respond before pulling `nomic-embed-text`. In `.env`, set `OLLAMA_BASE_URL=http://host.docker.internal:11434` and `OLLAMA_EMBEDDING_MODEL=nomic-embed-text`, then run `python scripts/local_setup.py`. Setup recognizes the external service and skips the bundled container bootstrap while still checking real inference. This path was clean-install tested with a separate native process and newly downloaded model; the bundled image download remains unverified on the test network. See [local setup](docs/local-setup.md) for isolation and network notes.

## Stop and restart

```sh
docker compose --profile ollama up -d
docker compose --profile ollama down
```

Volumes retain memory and the downloaded model. The default model is `nomic-embed-text` through local Ollama. No extra LLM or external inference key is required.
