# Retrieval and reader context audit

The complete local retrieval run contains 4,608 result rows, representing 1,536
eligible questions evaluated by three methods. The recorded aggregate recall
values were recomputed from the ten conversation checkpoints and matched.
It excludes 446 adversarial questions and four questions without evidence
annotations. Previously examined conversations are included.

| Method | Evidence recall | All evidence present | Multi-hop recall |
| --- | ---: | ---: | ---: |
| Keyword BM25 | 81.21% | 75.33% | 49.46% |
| Cosine | 69.76% | 63.35% | 49.67% |
| Compact RRF/MMR | 80.60% | 74.28% | 55.65% |

All methods use eight-turn chunks, at most eight results and the same
10,000-character ceiling. The compact ranker improves multi-hop recall while
keyword retrieval has the higher overall score. This evidence supports retaining
both baselines in future experiments.

## Context reaching the answering model

The answer pilot supplies a 4,000-character context. Retrieval reports previously
used larger ceilings. The cache-only audit reran 233 eligible questions in
conversations 1 and 2 at both ceilings using the same source vectors and ordering.

| Method | Recall at 4,000 characters | Recall at 10,000 characters |
| --- | ---: | ---: |
| Cosine | 60.64% | 74.06% |
| Keyword BM25 | 73.58% | 83.66% |
| Compact RRF/MMR | 71.87% | 82.46% |

The compact method loses 10.59 percentage points of evidence recall when its
context is reduced to the actual reader ceiling. Keyword retrieval also exceeds
the compact method at that smaller ceiling. The audit is post-hoc diagnosis on
previously evaluated data. No inference service was used.

## Available answer failures

The successful CI run retained aggregate outputs only. Its 5/10 cosine and 4/10
compact answer counts cannot be diagnosed question by question from that
artifact. The older laptop trial retains 20 attempts, of which six timed out.
Its results identify failure modes to test, with a different execution context
from the successful CI run.

- One multi-hop answer succeeds with cosine context. The compact context omits
  both annotated supporting turns and the reader abstains.
- A temporal question lacks the annotated event in both contexts. The reader
  substitutes the date of a different event.
- An adversarial question produces an unsupported specific answer with compact
  context, while the cosine answer abstains.
- At least one multi-hop answer omits a required fact despite the relevant
  source-turn identifiers appearing in its compact context. Source presence
  alone does not ensure that the reader interprets all required facts.

These observations support investigating context selection, temporal grounding
and unsupported-answer rejection. They do not establish the causes of the
successful CI run's individual mistakes.

## Next reproducible comparison

1. Freeze cosine, keyword BM25 and compact RRF/MMR as three retrieval arms with
   the same 4,000-character ceiling and question set.
2. Report supporting evidence in the exact context delivered to the reader.
   Record token counts too, including the prompt and reserved output. Verify the
   configured model window can hold the complete prompt.
3. Use the same reader weights, prompts and decoding parameters across arms.
   Retain failed requests in the denominator. Freeze all configuration before
   generating answers.
4. Use a separate calibrated local judge and retain responses privately for
   error analysis. Manually review disagreements and a fixed seeded sample.
   Export aggregates without raw dataset material or credentials.
5. Run an equal-budget second experiment with source-based temporal grounding
   only after the first results have been recorded. Keep the original frozen
   results for comparison and disclose prior dataset exposure.

Run the completed cache audit from the repository root:

```powershell
python -m benchmarks.context_budget_audit --data <pinned-locomo10.json> --ranking-dir <compact-v2-directory> --output <new-aggregate.json>
```

The original full run remains outside the checkout under
`openpeople/workspace/research/remembr-full-retrieval-2026-11-11`.
The frozen dataset SHA-256 is
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
These are offline retrieval measurements and a diagnostic plan. API latency,
full answer accuracy and competitor superiority remain unverified.
