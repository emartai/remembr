# Preserve complete evidence under a fixed context budget

The 50-question answer audit found failures when the answerer lacked evidence
and when it misread evidence. The follow-up keeps retrieval rankings frozen
and tests packing alone. Complete-turn packing retains timestamps and skips
turns that do not fit. The query-first variant chooses whole turns by lexical
relevance, then restores their order within each source.

All three methods stay within 4,000 rendered characters. Results cover 233
annotated questions from two previously evaluated LoCoMo conversations.

| Ranker | Evidence recall, slicing | Complete turns | Query-first turns |
| --- | ---: | ---: | ---: |
| Cosine | 60.64% | 61.07% | 63.53% |
| BM25 | 73.58% | 73.58% | 71.24% |
| Compact RRF/MMR | 71.87% | 71.87% | 70.49% |

Complete-turn packing saved roughly 25–28 characters per prompt on average
while retaining the same or slightly more evidence. Query-first helped cosine
but hurt the two stronger lexical and hybrid configurations. Neither result
justifies a change to production ranking or packing. This test uses cached
embeddings and measures evidence recall, not answer accuracy or latency.

Run `python -m benchmarks.complete_turn_context --data <pinned-locomo10.json>
--ranking-dir <frozen-ranking-directory>` from the repository root.

The next reader experiment should grade answers from both retrieved and
annotated source evidence on the same questions. Keep annotated evidence in a
separate diagnostic arm so it never enters the product index. This identifies
which misses persist even when the reader has the right source. Include
unsupported answers, dates, updated facts and correct abstentions in the
comparison. For the shared-project API, test these capabilities using sourced
corrections and revoked credentials across real agent sessions.

[LongMemEval](https://arxiv.org/abs/2410.10813) defines temporal reasoning,
knowledge updates and abstention as separate capabilities.
[EvalMem](https://arxiv.org/abs/2609.22231) describes the oracle-evidence
diagnostic. [Hindsight's recall interface](https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/api/recall.md)
documents how consolidated observations carry evidence and history.
