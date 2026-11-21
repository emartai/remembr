"""Measure complete-turn packing against character slicing on frozen retrieval."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from benchmarks.locomo import (
    DATASET_SHA256,
    TURN_ID,
    chunks,
    evidence_metrics,
    visible_turns,
)
from benchmarks.ranking_ablation import pack
from server.app.ranking import lexical_scores, rank


def pack_complete(documents, order, budget, query=None):
    """Keep source timestamps and whole turns, skipping turns that cannot fit."""
    parts = {}
    used = 0
    headers = {}
    candidates = []
    for index in order:
        header, *turns = documents[index].splitlines()
        headers[index] = header
        candidates.extend(
            (index, position, turn) for position, turn in enumerate(turns)
        )
    if query and candidates:
        scores = lexical_scores(
            query, [text.split(" ", 1)[-1] for _, _, text in candidates]
        )
        candidates = [
            row
            for _, row in sorted(
                zip(scores, candidates, strict=True), key=lambda pair: -pair[0]
            )
        ]
    for index, position, turn in candidates:
        cost = len(turn) + 1
        if index not in parts:
            cost += len(headers[index]) + (2 if parts else 0)
        if used + cost <= budget:
            parts.setdefault(index, []).append((position, turn))
            used += cost
    result = "\n\n".join(
        "\n".join([headers[index], *(turn for _, turn in sorted(parts[index]))])
        for index in order
        if index in parts
    )
    return result, visible_turns({"content": result})


def compare(dataset, ranking_dir):
    raw = dataset.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise ValueError("Unexpected LoCoMo bytes")
    samples = json.loads(raw)
    protocol = json.loads((ranking_dir / "ranking-protocol.json").read_text())
    cache = json.loads((ranking_dir / "embedding-ablation-vectors.json").read_text())
    digest = protocol["embedding_digest"]

    def lookup(text):
        return cache[hashlib.sha256((digest + "\n" + text).encode()).hexdigest()]

    groups = {}
    for index in protocol["confirmation_indices"]:
        sample = samples[index]
        docs = [row["content"] for row in chunks(sample, 8)]
        vectors = [lookup("search_document: " + d) for d in docs]
        for qa in sample["qa"]:
            evidence = set(TURN_ID.findall(" ".join(qa.get("evidence", []))))
            if qa["category"] == 5 or not evidence:
                continue
            question = qa["question"]
            rankings = rank(
                question, docs, lookup("search_query: " + question), vectors
            )
            lexical = lexical_scores(question, docs)
            rankings["bm25"] = sorted(
                (i for i, score in enumerate(lexical) if score > 0),
                key=lambda i: (-lexical[i], i),
            )[:8]
            for ranker in ("cosine_8", "bm25", "rrf_mmr_compact_8"):
                order = rankings[ranker]
                # Reserve all separator characters so the sliced comparator
                # also stays within the literal rendered context ceiling.
                slice_budget = 4000 - 2 * max(0, len(order) - 1)
                for method, (context, visible) in (
                    ("sliced", pack(docs, order, slice_budget)),
                    ("complete_turns", pack_complete(docs, order, 4000)),
                    ("query_first_turns", pack_complete(docs, order, 4000, question)),
                ):
                    assert len(context) <= 4000
                    score = evidence_metrics(evidence, visible)
                    groups.setdefault((ranker, method), []).append(
                        (score["evidence_recall"], score["all_evidence"], len(context))
                    )
    return {
        "scope": "Exploratory cached retrieval on previously examined conversations",
        "dataset_sha256": DATASET_SHA256,
        "embedding_digest": digest,
        "context_chars": 4000,
        "methods": [
            {
                "ranker": ranker,
                "packing": method,
                "questions": len(rows),
                "recall": statistics.mean(row[0] for row in rows),
                "all_evidence": statistics.mean(row[1] for row in rows),
                "mean_chars": statistics.mean(row[2] for row in rows),
            }
            for (ranker, method), rows in groups.items()
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--ranking-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.data, args.ranking_dir), indent=2))
