# Remembr

[![CI](https://github.com/emartai/remembr/actions/workflows/ci.yml/badge.svg)](https://github.com/emartai/remembr/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/remembr)](https://pypi.org/project/remembr/)
[![npm version](https://img.shields.io/npm/v/@remembr/sdk)](https://www.npmjs.com/package/@remembr/sdk)
[![License](https://img.shields.io/github/license/emartai/remembr)](LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/remembr)](https://pypi.org/project/remembr/)

Remembr is a self-hosted, open-source memory layer for AI agents. One agent can save a project decision, another can correct it, and both can retrieve the latest version with its source and authenticated author.

**LangGraph saves a decision → Claude Code corrects it → Codex recalls the correction after a restart.** Each agent uses a separate credential to access the same project space. Use the [Memory Explorer](docs/shared-project-memory.md#explorer) to inspect current and previous decisions.

[Run the handoff](examples/shared-project-memory/) · [Join the developer pilot](docs/pilot.md)

## Quick start

Use Python 3.11+, Docker Compose v2 and a running Linux container engine. The first run downloads container images and an embedding model.

```sh
git clone --branch v0.2.2 https://github.com/emartai/remembr.git
cd remembr
python scripts/local_setup.py
python scripts/smoke_test.py
```

The smoke test exercises private memory and prints its result. Follow [Start using Remembr](docs/getting-started.md) to create an account and open the explorer at `http://localhost:8000/explorer`. Create a project space, issue a credential for each agent, and [run the shared-memory handoff](examples/shared-project-memory/). When finished, run `docker compose --profile ollama down` to stop the stack and keep its volumes.

The default Docker setup uses local Ollama embeddings for retrieval. Remembr needs no external inference API key in this setup. Each agent uses its own configured model for reasoning.

## Connect your agents

Remembr 0.2.2 is available on [GitHub](https://github.com/emartai/remembr/releases/tag/v0.2.2), [PyPI](https://pypi.org/project/remembr/0.2.2/) and [npm](https://www.npmjs.com/package/@remembr/sdk/v/0.2.2).

| I want to | Start here |
| --- | --- |
| Share project memory from a Python or TypeScript app | Install `remembr==0.2.2` or `@remembr/sdk@0.2.2` and use [project spaces](docs/shared-project-memory.md#sdks). |
| Connect Claude Code, Codex, or another MCP host | Install `remembr[mcp]==0.2.2` and follow the [agent connection guide](docs/agent-connections.md). |
| Add private session memory to an application | See the [Python SDK](sdk/python/) or [TypeScript SDK](sdk/typescript/) for store, search and delete examples. |
| Check an integration or framework version | See the [verified environments](docs/compatibility.md) and [framework quickstarts](https://emartai.github.io/remembr/docs/quickstart/langgraph). |

## Documentation and feedback

- [Self-hosting and configuration](docs/local-setup.md) · [API reference](docs/api-reference.md) · [Verification](docs/verification.md)
- [Report an issue](https://github.com/emartai/remembr/issues) · [Contribute](CONTRIBUTING.md) · [MIT license](LICENSE)
