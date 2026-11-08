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
