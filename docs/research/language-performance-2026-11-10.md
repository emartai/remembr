# Python, Rust and Go for Remembr

Recommendation, 10 November 2026: retain Python for the API, access controls,
SDK/MCP integration and orchestration. Optimize measured computational work
before considering a focused native component. A full server rewrite is not
justified by the current measurements and would add migration work before the
developer pilot.

## What a language change can affect

| Part | Current behavior | Recommended approach |
| --- | --- | --- |
| API and permissions | FastAPI coordinates asynchronous database and model-service calls | Keep Python; measure per-stage latency and concurrency |
| Vector storage/search | PostgreSQL/pgvector executes vector operations | Tune queries and, when justified, model/dimension-scoped indexes with isolation/recall tests |
| Embedding and LLM inference | Ollama runs as a separate service | Measure model/hardware/batching costs; an API-language rewrite does not directly accelerate this service |
| Experimental reranking | CPU work over a bounded set of authorized source vectors | Reduce repeated computation; consider compiled array operations next |
| A future native ranking module | Not currently needed by evidence | Prefer a small Rust/PyO3 extension if profiling still justifies it |
| A future high-throughput collector or gateway | No current pilot requirement establishes this bottleneck | Consider Go as a separate service only after workload measurements |

This ordering is an engineering recommendation for this repository, not a
general claim that Python is faster than Rust or Go. Compiled implementations
can outperform Python loops in CPU-heavy work. They do not automatically reduce
model-service, network or database time.

FastAPI describes asynchronous handling of waiting/I/O and the distinction from
CPU parallelism. Python's asyncio documentation warns that CPU calculations can
block the event loop. The experimental API now offloads its pure ranking function
to a worker thread for responsiveness; this does not promise multicore speedup
for Python loops. [FastAPI concurrency](https://fastapi.tiangolo.com/async/),
[Python asyncio](https://docs.python.org/3/library/asyncio-dev.html#running-blocking-code).

NumPy performs many array operations in compiled code, offering a way to retain
the Python interface while accelerating numerical work. PyO3 supports focused
Rust extensions without replacing the Python application. Go remains a possible
choice for a separate service; it brings its own runtime and operational tradeoffs.
[NumPy](https://numpy.org/doc/stable/user/whatisnumpy.html),
[PyO3](https://pyo3.rs/), [Go runtime guide](https://go.dev/doc/gc-guide),
[pgvector](https://github.com/pgvector/pgvector).

## Measurement in this codebase

Inspection found that MMR repeatedly recomputed the same candidate-to-selected
cosine similarities. The optimization keeps each remaining candidate's maximum
redundancy and updates it only when a new item is selected. It also avoids
duplicating identical fused-rank calculations. Ranking formulas and selection
rules are retained.

On the Windows i5-8365U laptop, a synthetic CPU-only probe used 200 candidate
memories, 768-dimensional Python float vectors, seed 42 and three repetitions:

| Measurement | Median |
| --- | ---: |
| Original full rank order | 4,088.6 ms |
| Initial optimized measurement | 354.0 ms |
| Follow-up optimized measurement | 805.8 ms |

The initial comparison was approximately 11.5× faster; the follow-up was about
5.1× relative to the original median. Report both rather than selecting the best
result. Host conditions were not controlled as a dedicated performance lab.
The output-order hash matched in every comparison. The source snapshots,
individual repetitions and scope are in
[the measurement artifact](https://github.com/emartai/remembr/blob/main/benchmarks/results/ranking-cpu-2026-11-10.json).

Tests compare the incremental algorithm with the direct mathematical reference,
including negative similarities, tie-breaking, multiple relevance weights and
different limits. Another test bounds repeated cosine evaluations; another
checks that the API's first eight results match the evaluated compact ranker.

This measures one ranking function, not database work, ORM-array conversion,
Ollama, HTTP handling or p50/p95 under concurrent requests. It is not a Rust/Go
benchmark and does not show that the whole product is 5–11× faster. Run
`python -m benchmarks.ranking_performance --work-dir <outside-checkout-dir>` for
the current synthetic probe.

## Decision after the pilot

Trace embedding, database, reranking and request overhead separately. Test
representative corpus sizes and concurrency; report p50, p95, errors, throughput
and peak memory alongside answer/evidence quality. Use the same hardware and
workload for any Python/NumPy/Rust/Go comparison.

If numerical work remains the bottleneck, first compare native array operations
with the optimized reference. A Rust extension is the next candidate if that
still misses an agreed target. Preserve API behavior, permissions, correction
semantics and cross-platform installation tests. A full API rewrite or an extra
Go service needs its own measured benefit before becoming a roadmap commitment.
