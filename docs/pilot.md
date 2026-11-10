# Developer pilot

Start with 3–5 developers who already use two agent environments. This pilot
tests useful shared memory and onboarding; it is not a hosted-service launch or
a competitor benchmark. Each developer can self-host, keeping project data on
their own machine. No external LLM key is required by Remembr's default local
embedding path. The agent's own model/account remains the developer's choice.

## Setup

1. Use the maintainer-verified merged server commit and record `git rev-parse
   HEAD`. Build from that source. The original v0.2.1 server tag predates migration
   010; see [verification](verification.md). Preserve existing volumes when
   updating, and run the documented migrations.
2. Follow [Start using Remembr](getting-started.md) with the published Python
   SDK/MCP bridge. npm publication of the updated shared-project SDK is still
   pending; TypeScript users can use the HTTP API or the verified source package.
3. Create one project and a dedicated pilot space. Issue a different principal
   credential to each agent connection; grant only the access each connection
   needs. Follow [agent connections](agent-connections.md).
4. Confirm readiness, then store and retrieve one synthetic decision. Start with
   the documented defaults. Optional Nomic task prefixes require a fresh space
   or re-embedded memories and matching API/worker settings.

## Acceptance task

Use a small real project decision, such as the chosen database or a coding
convention. The developer should verify the result, not just accept a model's
statement that it used memory.

1. Agent A saves the decision with a source reference.
2. A separate agent connection B retrieves it in a new session and identifies
   its source and authenticated author.
3. B corrects the decision. A and a third connection, when available, retrieve
   the correction; the original remains identifiable in history.
4. Restart the API/worker containers without deleting volumes. The same
   credentials still retrieve the corrected memory.
5. Revoke a test connection and confirm it loses access while other authorized
   connections keep working. Check that a read-only connection cannot write.
6. Resume the project the next day and note whether the recalled information
   actually helped complete a task.

The release's live probe covers five independent Remembr credentials and real
API/worker restarts. Actual provider login switching should be checked in each
participant's intended client profiles; it is not inferred from that probe.
Agents must call the tools—Remembr does not import account chat histories.

## Recovery and optional ranking

If an embedding fails, restore the local provider/worker and use the documented
[retry endpoint](shared-project-memory.md#recover-a-failed-embedding-without-duplicating-memory).
Keep the original memory ID instead of saving a duplicate.

Developers experimenting through HTTP can compare `ranking: "rrf_mmr"` with the
default weighted hybrid mode in a dedicated space. The experimental option is
bounded to 200 ready compatible memories and a 10,000-character ceiling. Its
held-out retrieval gains do not guarantee better answers for every task. See
the [evaluation record](research/local-ranking-2026-11-10.md).

Stop Docker containers when no longer using them. `docker compose stop`
preserves the containers and their volumes; restart them for the next session.
Do not remove data volumes as part of an ordinary restart.

## Feedback to collect

For each participant, record:

- Server commit, SDK/client versions, OS and the two agent environments used.
- Setup completion, elapsed time and the first instruction that was unclear.
- Whether the acceptance steps passed, with request IDs for failures.
- One useful recall and one irrelevant, missing or stale recall, if encountered.
- Whether they returned to use Remembr on another day and which task it helped.
- Their most important improvement before they would recommend it.

Share sanitized diagnostics rather than credentials or private project content.
Prioritize onboarding failures, wrong permissions, failed processing and stale
recall before expanding features. After the first 3–5 participants, publish an
honest summary of adoption and failures and decide the next iteration from that
evidence. Benchmark superiority and managed-cloud availability remain separate
claims requiring separate verification.
