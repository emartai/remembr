# Local memory retrieval pilots, 8 November 2026

Task-specific Nomic prefixes improved mean supporting-evidence recall on two
small LoCoMo conversation samples. Answer accuracy and superiority over a
competitor remain unmeasured.

| Conversation | Mode | Eligible evidence questions | Mean evidence recall@8 | All evidence@8 | Mean context tokens | API p50 / p95 (ms) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Development, index 0 | Legacy | 19 | 60.5% | 52.6% | 1,797.6 | 390 / 889 |
| Development, index 0 | Nomic prefixes | 19 | 76.3% | 63.2% | 2,384.8 | 271 / 366 |
| Unused confirmation, index 3 | Legacy | 20 | 62.1% | 55.0% | 1,581.6 | 242 / 428 |
| Unused confirmation, index 3 | Nomic prefixes | 20 | 71.3% | 60.0% | 2,023.2 | 289 / 514 |

Each run attempted 25 seeded questions: five per category, including five
adversarial questions excluded from evidence-recall scoring. One development
question lacked evidence annotations. All 100 measured retrieval requests
succeeded. These are two conversations tested in two configurations, not 100
independent questions or the full dataset.

Both configurations used eight turns per source chunk, eight results, hybrid
search, a 12,000-character context ceiling and seed 42. There were 61 source
chunks in the development conversation and 90 in the unused conversation.
Every chunk was ready before its retrieval run. Only original conversation
turns, timestamps and supplied image captions entered memory. The dataset was
pinned to commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376` and SHA-256
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.

The local embedding model was `nomic-embed-text:publisher-f16`, digest
`ae3dba817a77ebc3d953c00121d5817de015c77eeb969a114df46a1ffb1eb6fd`,
with 768-dimensional vectors. Tests used native Ollama CPU inference and Docker
Desktop on an 8 GB Windows laptop. Legacy API runs used the existing image
`sha256:cbd49e0608cd6407269fe7e7c9f8a00be639947afa57a66893048a570c6d313e`;
candidate API/worker containers used that runtime with the modified server
source mounted. Both used separate synthetic tenants and isolated worker queues.
The candidate change is opt-in and records a different embedding identity.

## What the results support

The prefix change warrants wider testing: development recall gained 15.8
percentage points and the unused-conversation recall gained 9.2 points. It also
returned more tokens despite equal ceilings. The confirmation sample's multi-hop
recall fell from 48.3% to 45.0%, while open-domain recall increased from 20% to
40% and single-hop recall from 80% to 100%. These category samples contain only
five questions each. Temporal recall was 100% in both confirmation runs.

The clearest next investigation is multi-hop evidence coverage and context
efficiency. Test ranking, source-aware chunking and optional reranking on fresh
conversations before choosing another default.

## What the results do not support

Latency comes from single runs at different times, partly concurrent with
regression tests and a documentation build. Warm-up calls were excluded, but
there was no repeated, controlled latency study. The confirmation candidate was
slower than its baseline. Do not use these timings to claim lower latency than
a competitor or a universal speed improvement.

Context tokens use `cl100k_base`, not the Qwen tokenizer. Full/retrieved-context
ratios were approximately 10.7× → 8.0× for development and 15.6× → 12.2× for
confirmation. They exclude instructions, output and judging, and measure neither
financial savings nor LongMemEval-S performance.

The Qwen3 1.7B local answer trial completed only three answers before a later
600-second request timeout. No independent judge or complete answer benchmark
finished. These pilots cannot substantiate a 92.2% answer-accuracy comparison,
22.6× LongMemEval-S reduction, or a claim that Remembr is the best memory tool.

The complete aggregate values are in
[the result artifact](https://github.com/emartai/remembr/blob/main/benchmarks/results/local-pilots-2026-11-08.json).
Raw data, credentials and per-question outputs remain outside the repository.
See the [research and proposed build order](memory-competition-2026-11-08.md).
