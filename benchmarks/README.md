# Local memory evaluation

This harness measures the real shared-project-memory HTTP API. It is experimental
evaluation tooling, not a published accuracy score or a competitor ranking.
Ollama is the default answering provider. Nothing automatically downloads a model
or falls back to a paid service.

## Reproduce a retrieval pilot

Start Remembr and your local Ollama embedding model first. Install `tiktoken` in
the Python environment running the harness. Run from the repository root:

```powershell
$work = 'C:\Users\DELL\EmartAI\benchmark-runs\locomo-local-001'
python -m benchmarks.locomo prepare --work-dir $work
python -m benchmarks.locomo ingest --work-dir $work
python -m benchmarks.locomo retrieve --work-dir $work
python -m benchmarks.locomo summarize --work-dir $work
```

The work directory **must be outside this checkout**. Preparation downloads the
pinned official dataset if absent and verifies its SHA-256. Inference remains
local. Dataset access is the only required external request for this sequence;
copy the pinned `locomo10.json` into the work directory first for offline use.

Defaults: conversation index 0, 25 seeded category-stratified questions, eight
turns per chunk, eight results, 12,000 characters of retrieved context, hybrid
search, seed 42. Questions with no evidence annotations are excluded from
evidence metrics, with their category counts reported. Category 5 measures
abstention only in a separately scored answer run.

Use `--start-conversation 3` for an unused-conversation confirmation pilot.
Use `--conversations 10 --question-limit 0` for the complete corpus and all
questions. Repeat the exact corpus/search arguments in prepare, ingest and
retrieve: the manifest refuses a changed configuration in the same directory.
Keep separate work directories for every candidate. The current manifest calls
all runs development pilots; it does not certify a held-out release evaluation.

Only raw conversation turns, timestamps and provided image captions enter
memory. Reference answers, evidence labels and generated observations do not.
Ingestion creates an isolated synthetic account and verifies **every** memory
is ready before retrieval. A failed embedding aborts the run. Restore the
provider and explicitly retry failed jobs before resuming; re-running ingestion
does not itself retry failed jobs. Existing successful results are not silently
overwritten. Warm-up requests and pacing delays are outside measured latency.

## Optional local answer run

```powershell
python -m benchmarks.locomo answer --work-dir $work --provider ollama --model qwen3:1.7b --answer-limit 25
python -m benchmarks.locomo summarize --work-dir $work
```

The model must already be installed. The reader receives only the question and
retrieved context. Outputs checkpoint after every completed call. Report the
reader model digest, quantization, hardware, context budget, completion counts
and failures. Small CPU models can take minutes per question. Partial completion
is a diagnostic, not a representative accuracy estimate.

The reported token F1 is **unstemmed diagnostic F1**, not the official LoCoMo
metric. `judge` uses a custom exploratory correctness rubric, requires a
separate configured model by default, and never establishes superiority. A
self-judge requires an explicit flag and is labelled accordingly. Optional
remote adapters require explicit provider selection and free-account opt-in;
the default local workflow never calls them.

## Interpreting results

- Evidence recall: fraction of annotated supporting turns visible in the
  returned text. A truncated last line does not count as a complete turn.
- All-evidence rate: fraction of eligible questions with all supporting turns.
- Retrieval latency: client wall time for successful API calls, with errors
  reported separately. Report p50 and p95, warm/cold state and concurrent load.
- Context ratio: full-conversation tokens divided by retrieved-context tokens,
  using `cl100k_base`. This excludes answer/judge prompts and output tokens;
  it is not matched-model monetary savings.
- Judged answer accuracy: unmeasured until an explicit scoring protocol runs.

Pin the answerer, independent judge, prompts, dataset, corpus partition, memory
configuration and budgets before a release evaluation. Compare full-context,
no-memory and candidate systems with the same protocol. Report natural category
weights on a full run, uncertainty across conversations, failure denominators,
and answer quality alongside latency and token use. A small stratified pilot
cannot be compared directly to a vendor's full benchmark headline.

## Cleanup and artifacts

```powershell
python -m benchmarks.locomo cleanup --work-dir $work
```

Cleanup deletes only ledger-listed memories in this run's spaces after checking
their benchmark authorship and source marker, then revokes its principal. It
retains account/project metadata and local artifacts. Cleaned work directories
cannot be reused for ingestion or retrieval. Credentials, source data, vectors
and per-question results stay outside Git; only aggregate reports belong here.

The [official LoCoMo repository](https://github.com/snap-research/locomo) provides
the dataset and evaluation code. Its CC BY-NC 4.0 dataset terms are separate from
this project's software license. The harness does not redistribute that data.
LongMemEval is a separate benchmark and is not implemented by this runner.

For an offline cosine-only prefix ablation after a retrieval run:
`python -m benchmarks.embedding_ablation --work-dir $work`. This does not measure
Remembr API latency or answer accuracy.
## Broader local ranking and two-model pilots

`python -m benchmarks.ranking_ablation --work-dir <outside-checkout-dir> --data
<pinned-locomo10.json> --phase development` runs all annotated answerable
questions from conversation index 0. Its frozen protocol compares cosine,
positive-IDF BM25 rank fusion, diversity reranking and compact contexts.
`--phase confirmation` evaluates only the selected candidate and baseline on
unused conversation indices 1 and 2. Never reuse an existing run directory with
a different protocol. The first protocol's results are retained separately;
the compact second development iteration is disclosed in the research report.

Selection requires higher multi-hop recall, no overall recall loss and at most
10% growth in mean context tokens. The compact variants use a 10,000-character
ceiling, below the 12,000-character baseline ceiling. These are source-only
offline ranking evaluations. The functions are shared with the opt-in API
implementation; weighted hybrid remains the default. Their offline runtime is
not an API latency benchmark.

After confirmation, `python -m benchmarks.local_answer_pilot prepare --work-dir
<pilot-dir> --ranking-work-dir <ranking-dir> --data <pinned-locomo10.json>` freezes
five seeded questions per confirmation conversation, including adversarial
questions. Both variants receive the same 4,000-character reader ceiling. The
already-installed `qwen3:1.7b` reader and `qwen3:8b` judge use different
weights, sequentially, with 2,048-token windows and four CPU threads. This runner
does not download models; install the desired documented models locally first.

Run its `answer`, `judge` and `summarize` phases with the same `--work-dir`.
Answers and judgments checkpoint independently. Changed model digests, options
or frozen cases are rejected. Request failures and invalid judgments remain in
the denominator. Ten synthetic judge controls run before dataset evaluation;
passing them does not establish that the local judge is reliable on full LoCoMo.
This ten-question custom-rubric pilot is not official accuracy or evidence of
superiority over a competitor.

`python -m benchmarks.verify_shared_recovery --work-dir <outside-checkout-dir>`
uses the existing local `remembr-postgres` service and `remembr_default` network
to create its own temporary database, Redis, API and worker containers. It tests
a real provider outage, retry, API/worker restarts and five independent runtime
credentials, then removes only its own resources. Its hardcoded disposable DB
connection matches the development compose defaults. It is not a provider-login
switching test. Run the probe only after starting PostgreSQL; stop PostgreSQL
when finished if no other work needs it. Cleanup logging is best effort and must
never prevent stopping owned containers.

## GitHub quality workflow without LLM API keys

The **Local-model memory quality** workflow runs Ollama, Nomic and two Qwen3 models
inside a standard GitHub-hosted Linux runner. It requires no provider key and
makes no external inference requests. Downloads fetch public model weights,
tokenizer data and the pinned dataset. This runs on GitHub's cloud VM, not the
developer's laptop. [GitHub documents the public runner resources](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).

Use Actions → Local-model memory quality → Run workflow. The reader/judge phase
can be disabled for retrieval-only runs. The workflow tests itself on a PR that
changes its own YAML; other PRs retain fast regression/integrity checks.
The runtime is pinned to Ollama 0.35.1. The runner uses registry model
`nomic-embed-text:v1.5`; the laptop's custom `publisher-f16` packaging is distinct,
so compare candidates within a run and retain the recorded model digests.

Only allowlisted aggregate JSON and Markdown are uploaded, retained for seven
days. Raw QA, per-question responses, vectors, credentials and weights are
excluded. Request failures, invalid judging or failed sanity controls make the
answer evaluation fail rather than silently dropping cases. The owned Ollama
service is stopped in an `always()` cleanup step.

