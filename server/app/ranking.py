"""Source-only compact rank fusion shared by the API and evaluation harness."""

import math
import re
import statistics
from collections import Counter


def cosine(left, right):
    norm = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / norm if norm else 0


STOP = set(
    (
        "a an the and or is are was were to of in on for with what which who how does did do "
        "has have had it she he they her his their that this as at from by"
    ).split()
)


def terms(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in STOP]


def lexical_scores(query, documents):
    """BM25 with positive log1p IDF; no stemming, unlike PostgreSQL full text."""
    counts = [Counter(terms(doc)) for doc in documents]
    lengths = [sum(c.values()) for c in counts]
    average = statistics.mean(lengths) or 1
    frequencies = Counter(t for c in counts for t in c)
    scores = []
    for count, length in zip(counts, lengths, strict=True):
        score = 0.0
        for term in set(terms(query)):
            tf = count[term]
            if tf:
                idf = math.log1p(
                    (len(documents) - frequencies[term] + 0.5) / (frequencies[term] + 0.5)
                )
                score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * length / average))
        scores.append(score)
    return scores


def fuse(rankings, k=60):
    scores = Counter()
    for ranking in rankings:
        for position, index in enumerate(dict.fromkeys(ranking), 1):
            scores[index] += 1 / (k + position)
    return sorted(scores, key=lambda i: (-scores[i], i)), scores


def diversify(order, relevance, vectors, limit, weight=0.85):
    selected = []
    remaining = list(order[:40])
    maximum = max((relevance[i] for i in remaining), default=1) or 1
    redundancy = {index: None for index in remaining}
    while remaining and len(selected) < limit:

        def score(index):
            penalty = redundancy[index]
            return weight * relevance[index] / maximum - (1 - weight) * (
                penalty if penalty is not None else 0
            )

        best = max(remaining, key=lambda i: (score(i), -i))
        selected.append(best)
        remaining.remove(best)
        if len(selected) < limit:
            for index in remaining:
                similarity = cosine(vectors[index], vectors[best])
                previous = redundancy[index]
                redundancy[index] = (
                    max(previous, similarity) if previous is not None else similarity
                )
    return selected


def rank(query, documents, query_vector, vectors):
    """Inputs contain only source text and a question, never evaluation labels."""
    semantic = [cosine(query_vector, v) for v in vectors]
    ordered = sorted(range(len(vectors)), key=lambda i: (-semantic[i], i))
    lexical = lexical_scores(query, documents)
    keyword_order = sorted(
        (i for i, score in enumerate(lexical) if score > 0),
        key=lambda i: (-lexical[i], i),
    )
    fused, scores = fuse([ordered[:40], keyword_order[:40]])
    diverse_fused = diversify(fused, scores, vectors, 8)
    return {
        "cosine_8": ordered[:8],
        "rrf_8": fused[:8],
        "mmr_8": diversify(ordered, semantic, vectors, 8),
        "rrf_mmr_8": list(diverse_fused),
        "cosine_16": ordered[:16],
        "rrf_compact_8": fused[:8],
        "rrf_mmr_compact_8": list(diverse_fused),
    }


def rank_order(query, documents, query_vector, vectors):
    """Full order whose first eight equal the evaluated compact ranker."""
    if not documents:
        return []
    semantic = [cosine(query_vector, v) for v in vectors]
    ordered = sorted(range(len(vectors)), key=lambda i: (-semantic[i], i))
    lexical = lexical_scores(query, documents)
    keyword_order = sorted(
        (i for i, score in enumerate(lexical) if score > 0),
        key=lambda i: (-lexical[i], i),
    )
    fused, scores = fuse([ordered[:40], keyword_order[:40]])
    diverse = diversify(fused, scores, vectors, min(40, len(fused)))
    selected = set(diverse)
    rest = [i for i in fused if i not in selected]
    selected.update(rest)
    return diverse + rest + [i for i in ordered if i not in selected]
