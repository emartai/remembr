# Broader local ranking and recovery evaluation

Recorded 10 November 2026. The initial measurements ran on the laptop; the CI
workflow runs models inside its GitHub runner. Downloads and GitHub operations are separate from
inference. The evaluated compact ranker is now shared with an **opt-in experimental
API path**; weighted hybrid remains the default. No competitor win is claimed.

## Retrieval experiment

The first development iteration compared cosine, reciprocal rank fusion (RRF),
maximal marginal relevance (MMR) and a larger result pool on all 150 annotated
answerable questions from conversation index 0. RRF plus MMR improved multi-hop
recall but increased context tokens by about 13.5%, failing the predeclared 10%
growth gate. That result was preserved rather than relabelled a passing run.

A second development iteration added compact fusion variants with a
10,000-character ceiling, below the 12,000-character baseline ceiling. The
selection rule stayed unchanged: improve multi-hop recall, preserve overall
recall and stay within 10% mean token growth. Ties prefer higher all-evidence
coverage, then fewer tokens. The selected compact RRF+MMR candidate was frozen
before testing conversation indices 1 and 2; those conversations were not used
to select or adjust the candidate.

| Metric | Development baseline | Development candidate | Confirmation baseline | Confirmation candidate |
| --- | ---: | ---: | ---: | ---: |
| Annotated answerable questions | 150 | 150 | 233 | 233 |
| Multi-hop questions | 32 | 32 | 42 | 42 |
| Mean supporting-evidence recall | 73.9% | 82.9% | 74.1% | 82.5% |
| Multi-hop supporting-evidence recall | 45.1% | 56.0% | 51.3% | 59.2% |
| Multi-hop all-evidence rate | 18.8% | 37.5% | 19.0% | 31.0% |
| Mean retrieved context tokens | 2,236.6 | 2,363.4 | 2,184.3 | 2,340.1 |

Both rankers use task-prefixed Nomic embeddings and eight-turn source chunks.
The candidate fuses semantic and positive-IDF BM25 ranks (depth 40, RRF constant
60), then applies MMR with relevance weight 0.85 and returns up to eight chunks.
The lexical implementation uses simple tokenization without stemming and differs
from PostgreSQL full-text ranking. Reference answers, QA categories and evidence
labels are not inputs to the ranker. Labels are used afterward for scoring and,
on development data only, candidate selection. Category 5 and questions without
evidence annotations are excluded from these retrieval-only metrics.

These are 383 distinct scored questions across three conversations, with two
conversations held out from development. They are not a full ten-conversation
benchmark, a statistically established win, judged answer accuracy or API latency.
Token counts use `cl100k_base` and exclude instructions, generated answers and
judging. Do not interpret their ratio as financial savings.

The pinned dataset and embedding digest are recorded in
[the aggregate artifact](https://github.com/emartai/remembr/blob/main/benchmarks/results/ranking-pilot-2026-11-10.json).
The frozen configuration and development-result hash prevent selecting a new
candidate from the confirmation outcome. Per-question outputs and vectors remain
outside the repository.

Algorithm references: [Cormack et al., RRF](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf),
[Robertson et al., Okapi/BM25](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/okapi_trec3.pdf),
and [Graphiti's documented ranking strategies](https://help.getzep.com/graphiti/working-with-data/searching).
These sources motivate the experiments; they do not validate Remembr's results.

## Credential sharing and recovery

The full local server suite passed **346 tests**, including new cases covering
five independent principals, correction visibility, revocation, write-only retry
responses, provider failure/recovery, pending-job requeueing and deletion during
inference. The existing tenant-boundary and retrieval regression tests also pass.

A separate live probe used a disposable database, Redis, API and solo worker.
It verified a real unavailable embedding endpoint, failure recording, retry of
the same memory after restoring the provider, queued corrections surviving a
worker restart, and five credentials retaining consistent correction authorship
after a real API restart. Revoking one principal left the others functional.

The first probe cleanup hit a Windows UTF-8 log-decoding error. The remaining
temporary API was stopped manually, its database removed, and the harness fixed
so log collection cannot prevent container shutdown. A regression test covers
that failure. All containers were stopped after Docker-backed verification;
original volumes and stored memories were preserved.

Five Remembr credentials are not five authenticated Claude/Codex account logins.
Actual client-profile switching still requires the intended profile/configuration
paths and a separate acceptance run. No provider account histories are mirrored
or automatically imported.

The new [retry endpoint](../shared-project-memory.md#recover-a-failed-embedding-without-duplicating-memory)
supports failed jobs and explicit operator-assisted pending-job recovery. It does
not implement an automatic database outbox or promise lossless recovery from
every possible crash.

## Local answer-and-judge protocol

The bounded pilot freezes five seeded questions per confirmation conversation,
one per category, including adversarial questions. Each of the ten questions is
answered for both variants at a 4,000-character reader-context ceiling. This is
smaller than the retrieval experiment's ceiling so the local reader fits its
2,048-token window. It must not be compared directly with the table above.

The reader is Qwen3 1.7B; the current separate judge is Qwen3 8B. Both run
inside the evaluator's own machine or CI runner. Model
digests, generation options and case hashes are frozen; prompts are defined in
the versioned harness. The judge sees reference and
candidate answers without variant labels. Eight synthetic sanity controls and all
request/invalid-output failures are reported. These small related model families
and a ten-question custom rubric cannot establish official LoCoMo accuracy or
superiority. See the [benchmark instructions](https://github.com/emartai/remembr/blob/main/benchmarks/README.md)
for the resumable phases and interpretation limits.

The first CI run completed all 20 reader requests, but its Qwen2.5 1.5B judge
returned false on every control and passed only 2/4 checks. Its answer scores
are invalid and must not be interpreted as system accuracy. The revised
protocol states that references are ground truth,
and requires all eight controls to pass before dataset evaluation. This is
judge calibration against synthetic controls, not tuning against LoCoMo answers.
Qwen2.5 7B subsequently passed 6/8 and was also rejected. The current configured
judge must pass all eight; no failed calibration is accepted as an accuracy score.

## Next evidence-backed techniques to investigate

These are proposed experiments, not implemented capabilities or prerequisites
for a small pilot. Keep source-only ingestion and held-out selection rules.

1. **Context-aware indexing.** Add short, source-supported session/entity context
   to ambiguous chunks. Compare it with raw indexing at the same reader budget,
   and audit generated context for invented facts. This adapts
   [contextual retrieval](https://www.anthropic.com/research/contextual-retrieval);
   its published results do not establish a Remembr gain.
2. **Temporal and fact-aware retrieval.** Distinguish event time from ingestion
   time, preserve changing facts and test source-linked fact keys plus temporal
   query expansion. The [LongMemEval paper](https://arxiv.org/abs/2410.10813)
   evaluates session decomposition, fact-augmented indexing and time-aware query
   expansion. Its benchmark is separate from the current LoCoMo pilots.
3. **A small local cross-encoder.** Rerank a bounded candidate pool using a model
   such as [MS MARCO MiniLM](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2).
   Measure evidence and answer quality against p95 latency, RAM and truncation.
   The model's own MS MARCO scores are not agent-memory scores.
4. **Separate evidence from derived knowledge.** Retain source-linked facts,
   experiences and summaries with explicit provenance and correction invalidation.
   [Hindsight](https://arxiv.org/abs/2512.12818) motivates separating evidence and
   inference. Extraction/reflection should remain optional, locally runnable and
   measured against the raw-source baseline.

Test one change at a time, beginning with actual pilot failures. More graphs or
model calls do not establish better memory. Superiority claims still need matched
answerers, scoring, full relevant benchmarks and measured tradeoffs.
