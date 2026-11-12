# Remembr: competitive research and proposed build order

Reviewed 8 November 2026. This is an engineering proposal, not a claim that
Remembr has beaten these systems. Vendor results below have not been reproduced.

## What competitors establish

| System | Relevant evidence from its own materials | Implication for Remembr |
| --- | --- | --- |
| Living Brain | Reports 92.2% judged accuracy on 1,540 LoCoMo questions and 464 ms median retrieval. Its 22.6× context reduction is on LongMemEval-S against a 116K-token baseline; these are separate evaluations. | We need matched datasets, answerers, scoring and budgets before claiming a win. Cross-agent memory is already a competitive category. |
| Mem0 | Publishes an ingestion → retrieval → answer/judge evaluation harness with resumable artifacts. | Publish the configuration and evaluation path, not just a percentage. |
| Hindsight | Documents retain/recall/reflect operations and retrieval using semantic, keyword, graph and temporal signals. | Test whether derived facts and temporal retrieval improve hard queries enough to justify their local compute cost. |
| Graphiti | Builds temporal knowledge graphs with hybrid search and reranking options. | Treat changing facts and historical validity as explicit retrieval problems. |
| Letta | Documents shared memory repositories with version history and checks for conflicting changes. | Multi-agent updates need clear concurrency behavior and provenance. |
| Supermemory | Documents APIs, coding-agent integrations, MCP and self-hosting. | Local hosting and multiple integrations alone do not establish a unique advantage. |

Sources: [Living Brain](https://livingbrain.com/),
[Mem0 evaluation harness](https://github.com/mem0ai/memory-benchmarks),
[Hindsight](https://github.com/vectorize-io/hindsight),
[Graphiti](https://github.com/getzep/graphiti),
[Letta shared repositories](https://docs.letta.com/agent-sdk/repositories),
[Supermemory documentation](https://supermemory.ai/docs).

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

We can launch a useful developer pilot with accurate feature claims while this
research continues. A public claim to be the best available memory tool is not
supported by the current evidence.
