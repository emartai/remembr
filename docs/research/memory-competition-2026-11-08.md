# Remembr: competitive research and proposed build order

Reviewed 8 and 11 November 2026. Vendor results below come from their publishers.

## What competitors establish

| System | Relevant evidence from its own materials | Implication for Remembr |
| --- | --- | --- |
| Living Brain | Reports 92.2% judged accuracy on 1,540 LoCoMo questions and 464 ms median retrieval. Its 22.6× context reduction is on LongMemEval-S against a 116K-token baseline; these are separate evaluations. | We need matched datasets, answerers, scoring and budgets before claiming a win. Cross-agent memory is already a competitive category. |
| Mem0 | Publishes an ingestion → retrieval → answer/judge evaluation harness with resumable artifacts. | Publish the configuration and evaluation path, not just a percentage. |
| Hindsight | Documents retain/recall/reflect operations and retrieval using semantic, keyword, graph and temporal signals. | Test whether derived facts and temporal retrieval improve hard queries enough to justify their local compute cost. |
| Graphiti | Builds temporal knowledge graphs with hybrid search and reranking options. | Treat changing facts and historical validity as explicit retrieval problems. |
| Letta | Documents shared memory repositories with version history and checks for conflicting changes. | Multi-agent updates need clear concurrency behavior and provenance. |
| Supermemory | Documents APIs, coding-agent integrations, MCP and self-hosting. | Local hosting and multiple integrations alone do not establish a unique advantage. |
| OpenViking | Agents can read a directory abstract, an overview, or the full source. Its repository links reproduction scripts and reports separate LoCoMo results for three agent integrations. | Test whether a short decision with an on-demand source costs fewer tokens across a complete handoff. Record which agent did the reading. |

Sources: [Living Brain](https://livingbrain.com/),
[Mem0 evaluation harness](https://github.com/mem0ai/memory-benchmarks),
[Hindsight](https://github.com/vectorize-io/hindsight),
[Graphiti](https://github.com/getzep/graphiti),
[Letta shared repositories](https://docs.letta.com/agent-sdk/repositories),
[Supermemory coding agents](https://supermemory.ai/coding-agents/),
[OpenViking](https://github.com/volcengine/OpenViking).

## Recommended product focus

My recommendation is to make Remembr especially reliable for permissioned
shared memory between coding agents and custom agents: who wrote a decision,
which source supports it, who can read or correct it, and whether a correction
survives a restart. This is a proposed focus, not an assertion that competitors
lack these capabilities. Validate it with users and task-level measurements.

## Build in this order

1. **Make evaluation reproducible.** Freeze corpus bytes, development and unused
   conversations, prompts, model digests, budgets and scoring before tuning.
   Separate supporting-evidence recall, answer accuracy, abstention, latency,
   tokens and errors. Keep raw labels out of ingestion. The new local LoCoMo
   harness is a starting point; full answer scoring and matched competitors
   remain unfinished. See the [benchmark instructions](https://github.com/emartai/remembr/blob/main/benchmarks/README.md).
2. **Correct embedding task formatting, then confirm generalization.** Nomic's
   model card specifies different document and query prefixes. An opt-in
   `OLLAMA_TASK_MODE=nomic_search` now implements them with a versioned vector
   identity. Re-embed memories before switching a deployment: historical raw
   vectors are intentionally incompatible. Keep `legacy` as the default until
   wider validation supports changing it.
3. **Improve hard retrieval with measured ablations.** Compare existing hybrid
   ranking with reciprocal-rank fusion, source-aware chunking and diversity.
   Add a small local reranker only if its evidence/answer gain justifies p95
   latency and RAM. Measure at equal context budgets; fetching more context is
   not free. Do not add a graph before establishing the failure it solves.
4. **Represent changing facts and uncertainty.** Prototype explicit validity
   times, historical queries and source-linked extracted facts. Preserve raw
   evidence, distinguish inferred facts, test correction chains, and teach the
   reader to abstain when support is missing. Extraction must be optional and
   local in this workflow; it needs its own quality evaluation.
5. **Strengthen recovery and permissions.** Reconcile saved-but-not-queued jobs,
   test provider outages, retries, worker restarts and deletion during inference.
   Continue testing tenant boundaries, grant revocation and cross-agent updates.
   Document recovery behavior users can actually rely on.
6. **Run real multi-agent tasks with 3–5 developers.** Measure setup completion,
   correct handoffs, correction recall after restart, repeat use and failures.
   Use these results to improve onboarding and choose the next integration.
7. **Consider hosted operation after repeat demand.** First establish recovery,
   observability, isolation, quotas and a clear support model. Keep local use
   available. No hosted release is implemented by this experiment.

The task-prefix requirement comes from the
[Nomic publisher model card](https://huggingface.co/nomic-ai/nomic-embed-text-v1.5).
The rest of this ordering is an engineering recommendation based on the product
and observed failure modes, rather than a benchmark-proven universal recipe.

## Local hardware limits and launch claims

The existing 8 GB laptop can run Nomic retrieval locally. The initial Qwen3 1.7B
answer trial completed only three questions, each taking roughly four to eight
minutes, before a later call timed out. This is not enough to judge system
accuracy. No paid inference or remote model is required by the retrieval work.
A complete local answer-and-judge evaluation needs a suitably capable local
machine, a bounded protocol, and honest completion/error reporting.

Before claiming better accuracy than Living Brain, finish the full relevant
question set, use a documented independent judge with manual spot checks, and
run matched baselines. Before claiming lower latency, match workload and disclose
hardware, concurrency and warm-up. Before claiming token savings, report answer
quality at the same time and include the same prompt components. LongMemEval-S
must be run separately for a claim against its 22.6× headline.

## Experiments for the local developer pilot

These are proposals in order of expected value to the pilot. Their ranking
reflects existing Remembr evidence and implementation cost. Each needs a
comparison on untouched tasks before it can support a product claim.

1. **Recover the current decision with its source.** Start with the existing
   correction and access-control APIs. Agent A records a decision referencing
   a commit. Agent B corrects it with a newer source. Restart the worker and
   API, revoke A, and ask C for the current decision and its evidence. Include
   another space with the same project terminology and a different decision.
   Score the decision, source and author separately. Count stale answers and
   unauthorized reads, including direct reads by a known memory ID. A query
   that returns no answer after revocation is correct only for the revoked
   credential. This extends the [recorded live recovery checks](local-ranking-2026-11-10.md).
2. **Read more evidence only when the task needs it.** Compare today's compact
   retrieval with returning the recorded decision and source identifier first.
   Let the agent request the authorized source detail in a second call. Test
   simple decisions and questions requiring two sources. Count tokens and
   elapsed time across *both* calls, verify citations, and include the cost of
   examining the wrong source. Recheck authorization on every detail read.
   Existing author-entered decision text makes this trial possible without an
   extra generation model. [OpenViking's context layers](https://github.com/volcengine/OpenViking)
3. **Handle edits from a stale session.** Start two agents from the same
   decision. Have B correct it, then have A submit a different correction from
   its older session. Repeat with simultaneous submissions in both orders.
   Record responses and inspect history for silently lost edits. Compare the
   current API with an expected-version check only if the trial exposes a
   failure. [Letta shared repository versions](https://docs.letta.com/agent-sdk/repositories)

## Comparing systems fairly

| Question | Workload and comparison | What to report |
| --- | --- | --- |
| Do agents recover the right project decision? | Use the same synthetic decisions, revisions, distractors, identities and source references. Compare Remembr with a checked-in decision file and runnable competitors. Record manual instructions and any adapter that supplies missing behavior. A file is a baseline for recall only. | Per-task decision correctness, source correctness, stale answers, unauthorized reads and time to first successful handoff. Score each capability separately. |
| Does better retrieval yield better answers? | Compare Remembr defaults, the experimental ranker, and available local competitor configurations. Ingest only original source turns. Freeze question IDs, document boundaries where supported, reader, answer budget, grading method and dataset version. Audit blinded paired answers against human labels, including disagreements and abstentions. | Counts per category, failures in the denominator, evidence recall, answer accuracy, paired gains and losses. Report uncertainty by conversation because questions within a conversation share evidence. |
| How expensive is each approach on the same machine? | Run one system at a time. Record OS, CPU, RAM, model digests, warm-up and simultaneous users. Measure insertion to searchable, full retrieval request, and end-to-end answer separately. Run identical warm requests and cold-start trials. | Median and p95 latency with request counts, peak memory, input/output tokens across all calls and completed tasks. Record model work at ingestion as well as at query time. |
| Can the competitor's headline be reproduced? | For Living Brain, match the 1,540 answerable LoCoMo questions for its accuracy claim. Run LongMemEval-S separately for context reduction and compare against the same full-context baseline. Keep hosted-only services as vendor-reported rows while inference must stay local. | List exact versions, models, scoring, coverage, and which settings differ. Leave comparisons with unavailable access or unknown methodology unmeasured. |

For local baselines, start with the checked-in file and Remembr defaults, then
Mem0 OSS and Graphiti with documented local providers. Add Hindsight and
OpenViking using their supported local setups where resources allow. Inspect
Letta and Supermemory separately for the shared-update and coding-agent
workflows. Record setup errors, resource limits and exact editions alongside
completed runs. The ChatAndBuild product in the benchmark row documents a
hosted API and MCP service. Its public documentation reviewed here did not
establish a self-hostable server. [Living Brain developer documentation](https://docs.livingbrain.com/)

Use the original [LoCoMo](https://github.com/snap-research/locomo) and
[LongMemEval](https://github.com/xiaowu0162/LongMemEval) protocols. Keep the
three conversations already used during ranker selection and confirmation
identified when reporting a full LoCoMo result. Report the remaining
conversations separately so prior exposure is visible.

## Launch order updated 11 November 2026

1. Diagnose the evaluation failure, verify the fix and merge the reviewed code.
2. Rehearse a clean installation and the cross-agent correction, restart and
   revocation workflow against the merged commit.
3. Finish the benchmark runs, review the judge against human-scored examples,
   and document the results and limitations of each competitor comparison.
4. Publish and install-check the Python and npm packages. Finish the quickstart,
   compatibility notes, changelog and two-agent demo.
5. Run the private pilot with 3–5 developers, including real account switching
   and next-day recall. Fix the issues they encounter and repeat affected tests.
6. Launch publicly with the verified packages, documentation and measured results.
   The managed-cloud decision can follow once developers are using Remembr.
