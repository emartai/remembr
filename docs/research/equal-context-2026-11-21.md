# Equal context answer benchmark

The [50-question run](https://github.com/emartai/remembr/actions/runs/44823831922)
evaluated all three retrieval methods on the same seeded LoCoMo questions from
conversations 1 and 2. The run used the same Qwen3 1.7B reader, Qwen3 8B judge,
and 4,000-character source allowance per question. Both models ran in Ollama
on the GitHub runner. All 150 cases completed and the judge passed 10 controls.

| Retrieval | Judged correct | Evidence recall in reader context (39 questions) | Mean prompt tokens |
| --- | ---: | ---: | ---: |
| BM25 | 19/50 | 67.7% | 1,126 |
| Cosine | 19/50 | 57.3% | 1,142 |
| Compact RRF/MMR | 20/50 | 60.3% | 1,141 |

The longest observed reader prompt used 1,301 tokens and no response hit the
output limit. On 11 adversarial questions, correct abstentions were 2 for BM25,
4 for cosine, and 3 for compact RRF/MMR. A manual spot check of five seeded
questions covered all three arms and agreed with the automated verdicts on
those 15 responses. One unanswerable question elicited a specific unsupported
date from every arm. Other reviewed misses included answers about a different
event and answers that omitted required facts. The spot review used the dataset
references and provides limited coverage.

Keep the experimental ranking opt-in. A one-answer difference in this sample
does not establish a quality gain. The two conversations were used in prior
experiments, and the custom scoring is separate from official LoCoMo accuracy.
These outcomes do not establish competitor superiority.
