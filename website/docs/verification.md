# Verification record

This records local acceptance of the source and SDK 0.2.1 candidates as of 1 November 2026. The source was subsequently merged as PR #73 and tagged v0.2.1; Python 0.2.1 is published on PyPI. npm 0.2.1 publication is pending. These checks do not establish production certification.

| Area | Completed verification |
| --- | --- |
| SDK baseline | 54 Python tests, 20 TypeScript tests, builds and installed-package HTTP probes |
| API/database | 77 selected regression tests covering filters, isolation, idempotency and non-superuser row-level security |
| Runtime | 13 focused regressions, 18 stability samples, worker outage/recovery and queued embedding recovery |
| Agent handoff | Real LangGraph write → Claude Code MCP correction → API/worker recreation → Codex MCP recall; separate credentials, authorship, lineage, read-only denial and revocation |
| Explorer | 19 Chromium browser checks and screenshot review; 12 PostgreSQL/asset regressions; 320/390 px layouts |
| Clean install | Separate source copy, empty database/Redis volumes, migrations 001–009, fresh Docker builds and native Ollama model download |
| Package consumers | Installed Python wheel with MCP and sdist without MCP; Python sync/async, npm CommonJS/ESM, four installed MCP tools, and quickstart smoke |

These are separate checks with overlapping coverage; their counts are not a combined test-suite total. Browser pending/failed/error rendering included controlled responses; lifecycle operations and semantic retrieval used the live API. See [compatibility](compatibility.md) for versions and [local setup](local-setup.md) for reproduction instructions. The browser harness is `scripts/test_explorer_browser.py`.

The clean-install inference path used native Windows Ollama with an empty model directory and a fresh `nomic-embed-text` download. The bundled Ollama Docker image download failed with premature EOF and remains unverified. Docker build networking required temporary host-resolved entries in a verification-only override; fixed IPs and that override are not included in the product.

Firefox/WebKit, physical devices, a full framework-version matrix, durable graph checkpoint recovery, hosted operations and production guarantees were not established. Existing framework adapters use private memory; shared spaces use the project SDK or MCP bridge. Detailed local logs and screenshots remain in the maintainer workspace rather than this public repository.


## Default Docker acceptance — 4 November 2026

The [clean Ubuntu runner acceptance](https://github.com/emartai/remembr/actions/runs/41885511938) passed using canonical `docker-compose.yml`, empty volumes, a fresh `ollama/ollama:latest` image (Ollama 0.40.14) and a downloaded `nomic-embed-text` model. Setup reached readiness and migrations 001–010 completed. The private-memory smoke passed queued embeddings, exact recall in all three modes, tenant isolation and deletion. The installed PyPI SDK 0.2.1 executed the actual shared-memory walkthrough, including registration/login, authenticated authorship and recall after API/worker recreation. The runner's disposable containers and volumes were removed afterward.

This run discovered a retained 1024-dimensional HNSW index left behind by the earlier column-widening migration. Migration 010 removes it without deleting memories or vectors, allowing the default 768-dimensional model and other dimensions to be stored. Private vector retrieval uses exact search after this change; large-data ANN performance is not established. The correction is in the current source, not the original v0.2.1 server tag. Earlier native-install checks did not establish that the untouched 001–009 migration path worked for default-model writes.

The Windows download retry still ended with premature EOF, so this establishes clean Linux installation rather than a completed bundled-Ollama installation on that laptop. See [local setup](local-setup.md) for repeatable commands.
