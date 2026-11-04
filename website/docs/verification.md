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
