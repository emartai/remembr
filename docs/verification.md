# Verification record

## 0.2.2 candidate package verification — 16 November 2026

The TypeScript tarball, Python wheel and Python source distribution built
outside the checkout. An isolated npm consumer loaded the tarball through
CommonJS and ESM and exposed the five shared-space methods. An isolated wheel
consumer imported the project API and MCP bridge. Twenty source and manifest
files were byte-compared with the current working tree on 16 November.

The build reused the installed TypeScript compiler and Python dependency
tooling. This verifies package contents and importability. The fresh Linux
server checks below supply the network-installation and live API evidence.
These candidate packages have not been published.

| Artifact | SHA-256 |
| --- | --- |
| remembr-sdk-0.2.2.tgz | `4ed3b06f21470f8e5a4cf7660a0ab2a387e2b10d31b3bdf039c7fe3e2db236c5` |
| remembr-0.2.2-py3-none-any.whl | `e83f7cb34d741c8f6007a310f0904650897578c7088111341d9cda508545e10e` |
| remembr-0.2.2.tar.gz | `a0f5f309f2e3a2808ead7c97994dd73b3a3f4a823f2b61e18025723cdd8729d5` |

## Release candidate verification — 12 November 2026

The follow-up [equal-context benchmark](research/equal-context-2026-11-21.md)
completed 150 cases across three retrieval methods. The experimental ranker
remains opt-in. The benchmark reports a separate [local competitor comparison](research/competitor-comparison-2026-11-16.md).

[PR #75](https://github.com/emartai/remembr/pull/75) merged at
`db027065bb06525deb50fac27612b81b4ec87156` after 25 applicable checks passed.
The [fresh Linux installation](https://github.com/emartai/remembr/actions/runs/43182769513)
used the published Python SDK and local Ollama. It verified two independent
agent credentials, source and author metadata, a correction surviving API and
worker recreation, and revocation of the reviewing credential while the first
agent retained access to the correction.

The [runner-local evaluation](https://github.com/emartai/remembr/actions/runs/43182769457)
passed ten judge controls and completed all twenty reader/judge cases. On its
ten paired questions, the cosine baseline answered five correctly and the
experimental ranker answered four correctly. The experimental ranker remains
opt-in. Its improved supporting-evidence recall on 233 questions has not
established an answer-quality improvement or competitor superiority.

On 14 November 2026, the registries served Python `remembr==0.2.1` and npm
`@remembr/sdk@0.2.0`. The updated TypeScript source package is version 0.2.1;
its publication remains pending authenticated npm publish access. Use the
merged server source above to include migration 010 and the latest fixes.

A fresh package probe on 14 November built both SDKs from an archive of the
verified PR head `7ff787509f0fc8974a9463862d7801ba02fac87c`. The resulting
TypeScript tarball passed installed CommonJS and ESM checks for all five
shared-space methods. The Python wheel and source distribution built, and an
isolated wheel consumer imported the project API and MCP bridge. This probe
reused installed compiler and Python dependency tooling; the Linux acceptance
above provides the clean network-installation evidence. Package verification
does not establish npm publication.

## Earlier acceptance — 1 November 2026

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
