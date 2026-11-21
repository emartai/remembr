# Local comparison protocol and competitor reproducibility

The completed full LoCoMo retrieval run evaluates 1,536 annotated answerable
questions across ten conversations, with 446 adversarial questions and four
unannotated questions excluded from evidence scoring. Three previously examined
conversations are included. The results therefore describe the supplied corpus
and disclosed configuration, with prior development exposure.

| Method | Supporting-evidence recall | All evidence present | Multi-hop recall |
| --- | ---: | ---: | ---: |
| Keyword BM25 | 81.21% | 75.33% | 49.46% |
| Cosine | 69.76% | 63.35% | 49.67% |
| Compact RRF/MMR | 80.60% | 74.28% | 55.65% |

All three methods receive the same raw conversation chunks and at most eight
results. Each context has a 10,000-character source-content allowance, with
inter-chunk separators added afterward. These figures measure retrieval of
annotated evidence. The separate reader experiment measures generated answers.
Model inference latency, HTTP service latency and dollar savings require their
own measurements.

The local cache audit was repeated on 16 November. At the reader's
4,000-character allowance, evidence recall on 233 questions was 60.64% for cosine,
73.58% for BM25 and 71.87% for compact RRF/MMR. Retaining BM25 in the next answer
comparison is warranted by these results. The audit uses previously recorded
vectors, so it does not establish embedding input truncation or throughput.

## Mem0 source-storage comparison

The runner in `benchmarks/mem0_source_comparison.py` installs the official Mem0
package in a separate Python environment and exercises its public
`Memory.add(..., infer=False)` and `Memory.search(...)` operations. The vector
store runs locally. A loopback HTTP adapter returns the same previously recorded
Nomic document/query vectors used by the other arms. It rejects uncached text
and generation requests.

The protocol uses conversations 1 and 2, eight-turn source chunks, eight retrieved
items and two context allowances of 4,000 and 10,000 characters. Each conversation
has a separate user scope. The runner checks that every returned source belongs
to that conversation. Fact extraction is disabled consistently for this
controlled source-storage comparison. The official Mem0 documentation supports
that mode and recommends inferred facts for its usual workflows.
[Mem0 add operation](https://docs.mem0.ai/core-concepts/memory-operations/add)

The comparison completed on 21 November with Mem0 2.2.1, Qdrant Client
1.20.0 and Ollama client 0.6.3. All 233 eligible queries completed for every
method. The adapter served 384 embedding requests and one model-list request.
Mem0 trims question whitespace, so the adapter maps those inputs to the same
frozen question vectors. Mem0's optional keyword dependency was absent.

| Method | Evidence recall at 4,000 characters | Evidence recall at 10,000 characters |
| --- | ---: | ---: |
| Mem0 source mode | 60.64% | 76.13% |
| Cosine | 60.64% | 74.06% |
| BM25 | 73.58% | 83.66% |
| Compact RRF/MMR | 71.87% | 82.46% |

The comparison measures a defined retrieval configuration using cached
embeddings. Mem0's fact-extraction performance, generated answers and
production latency remain unmeasured. The aggregate and exact version
information are in `benchmarks/results/mem0-source-2026-11-21.json`.

## What published competitor results require

| System | Published evaluation or deployment route | Requirement for a matched local run |
| --- | --- | --- |
| Mem0 | Its evaluation repository separates ingestion, search and answer/judge phases and provides an Ollama server configuration. Its normal ingestion extracts facts. | Enable the declared extraction configuration and count its inference cost; use the same answerer, judge, questions and output-context allowance across systems. |
| Graphiti | The official project supports Ollama-compatible generation, embeddings and reranking, with a graph database. | Pin the graph database and model versions, allow extraction to finish, and retain extraction failures in the report. |
| Hindsight | The official project supports local model providers including Ollama, plus its memory service and database. | Pin retain/recall configuration, wait for asynchronous ingestion, and account for the extraction and reflection calls used. |
| LangMem | Its tools use a LangGraph store and an agent to manage memories; the example uses an in-process store. | Declare the persistence backend and the agent's extraction/update policy before judging memory quality or restart behavior. |
| Living Brain | The benchmark claim describes its hosted product. | Obtain access and permission for a matching run; the local-only evaluation cannot reproduce the hosted system here. |

[Mem0 evaluation source](https://github.com/mem0ai/memory-benchmarks),
[Graphiti local setup](https://github.com/getzep/graphiti),
[Hindsight deployment](https://github.com/vectorize-io/hindsight),
[LangMem source](https://github.com/langchain-ai/langmem),
[Living Brain](https://livingbrain.com/).

Matching a dataset name alone does not match the experiment. Record the corpus
digest, answerable/adversarial selection, prior tuning exposure, extraction
model, embeddings, retrieved source count, complete prompt tokens, reader,
judge rubric, calibration, hardware and completion/error counts. Preserve the
raw answers privately for disagreement review. The tested Mem0 source mode and
the three local rankers must retain their configuration names in any public
table. Broader vendor accuracy rankings remain unverified.
