# Roadmap

Updated 29 October 2026. Remembr is a shared, persistent memory server for multi-agent systems across frameworks and coding tools.

This is a delivery plan, not a list of completed features or promised dates. Existing storage, sessions, local embeddings, SDKs, adapters and lifecycle features remain part of the product. Source availability does not replace release verification.

## Phase 0: Reliable release baseline

- Finish the prepared SDK fixes and validate built Python/npm packages.
- Correct semantic-search filters and test isolation, limits and fallback paths.
- Verify Docker, database migrations, worker and embedding-provider readiness.
- Demonstrate store, bounded processing wait, retrieval of the exact episode, and deletion.
- Document supported adapter versions and accurate setup requirements.

## Phase 1: Trusted sharing across runtimes

- Persistent project memory spaces separate from sessions and runs.
- Separate revocable credentials, read/write grants and authenticated authorship.
- Explicit source references, idempotency and concurrent-write rules.
- Thin MCP bridge using the same API contract as the SDKs.
- Tested LangGraph, Claude Code and Codex workflows and client instructions.
- Acceptance demo across three independent processes, distinct credentials and restarts, including denied-access cases.

## Phase 2: Understandable memory and adoption

- Small memory explorer, processing status and retrieval diagnostics.
- Bounded context, corrections, supersession, expiry and observable webhook delivery.
- Opt-in capture only where a host's lifecycle support is tested.
- Early external design partners and reproducible cross-runtime evaluations.

## Phase 3: Optional knowledge processing

- Source-linked extraction, summaries, temporal facts and conflict review.
- Evaluate confidence, decay and consolidation against a raw-episode baseline.
- Add knowledge-graph queries only when demonstrated tasks require them.

## Commercial track

Paid setup/support or manually operated hosting can follow verified operations and willingness to pay. Developer portal, advanced access controls, audit retention, SSO and enterprise deployments follow real requirements. Pricing, SLAs and certification remain uncommitted until supported by evidence.

## Retained longer-term directions

Procedural memory, suggested next steps, richer health/contribution analytics, PII controls, proactive routing, consent-based cross-app memory, alternative vector databases, multimodal memory, federation, GraphQL and a template ecosystem remain in the backlog. They do not block the first reliable shared-memory release.

## Planning source

The canonical full roadmap is maintained in the companion planning repository at `emartai.docs/remembr/remembr.md`. This page and the website roadmap are synchronized summaries. The 29 October review preserves the prior roadmaps and feature history; updating this document does not itself implement or release a capability.

## Release implementation progress

Shared project spaces, separate revocable agent credentials, read/write/delete grants, authenticated authorship, persistent retry keys and correction lineage are implemented locally. Python/TypeScript project APIs, a stdio MCP bridge and the small memory explorer are available in source. PostgreSQL authorization/lifecycle checks, live concurrency and TypeScript HTTP checks passed. The combined real LangGraph write → Claude Code MCP correction → API/worker recreation → Codex MCP recall passed on 31 October 2026 with distinct credentials, authenticated authorship and correction lineage. Read-only writes, grant removal and revocation were verified. See `openpeople/workspace/research/remembr-runtime-2026-10-31/REPORT.md` in the company workspace for the latest runtime acceptance evidence.

The explorer passed 19 real Chromium checks and screenshot review on 1 November 2026, including lifecycle, permissions, error recovery, disconnect and 320/390 px layouts. Twelve PostgreSQL/asset regressions passed; evidence is in `openpeople/workspace/research/remembr-explorer-2026-11-01/REPORT.md`. Existing adapters still target private memory; shared spaces use the project SDK or MCP. These changes were merged in PR #73 and tagged v0.2.1. Python 0.2.1 is published on PyPI; npm 0.2.1 publication remains pending. This delivery does not complete every Phase 1/2 item, the framework support matrix, durable graph checkpointing, webhook delivery or production certification. See the company workspace verification reports for evidence and limits.

On 4 November, public onboarding was updated for Python 0.2.1 and pending npm publication. A clean Ubuntu bundled-Ollama installation passed with migration 010, including private memory, the published SDK walkthrough and restart recall. See [verification](verification.md) for the vector-index fix and Windows network limitation.
