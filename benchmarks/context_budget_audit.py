"""Recheck frozen local evidence at the reader's actual context ceiling."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from benchmarks.locomo import DATASET_SHA256, TURN_ID, chunks, evidence_metrics
from benchmarks.ranking_ablation import pack
from server.app.ranking import rank, lexical_scores


def audit(data, ranking_dir):
    raw = data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise ValueError("Dataset digest differs")
    samples = json.loads(raw)
    protocol = json.loads((ranking_dir / "ranking-protocol.json").read_text())
    cache = json.loads((ranking_dir / "embedding-ablation-vectors.json").read_text())
    digest = protocol["embedding_digest"]

    def vector(text):
        return cache[hashlib.sha256((digest + "\n" + text).encode()).hexdigest()]

    rows = []
    for index in protocol["confirmation_indices"]:
        sample = samples[index]
        docs = [c["content"] for c in chunks(sample, protocol["turns_per_chunk"])]
        vectors = [vector("search_document: " + d) for d in docs]
        for qa in sample["qa"]:
            evidence = set(TURN_ID.findall(" ".join(qa.get("evidence", []))))
            if qa["category"] == 5 or not evidence:
                continue
            rankings = rank(
                qa["question"], docs, vector("search_query: " + qa["question"]), vectors
            )
            scores = lexical_scores(qa["question"], docs)
            rankings["bm25"] = sorted(
                (i for i, score in enumerate(scores) if score > 0),
                key=lambda i: (-scores[i], i),
            )[:8]
            for method in ("cosine_8", "bm25", "rrf_mmr_compact_8"):
                for budget in (4000, 10000):
                    _, visible = pack(docs, rankings[method], budget)
                    rows.append(
                        dict(
                            method=method,
                            budget=budget,
                            **evidence_metrics(evidence, visible),
                        )
                    )
    result = {
        "scope": "Post-hoc cached evidence diagnostic on previously evaluated conversations 1 and 2. No model generation or answer-quality claim.",
        "dataset_sha256": DATASET_SHA256,
        "embedding_digest": digest,
        "metrics": [],
    }
    for method in ("cosine_8", "bm25", "rrf_mmr_compact_8"):
        for budget in (4000, 10000):
            group = [r for r in rows if r["method"] == method and r["budget"] == budget]
            result["metrics"].append(
                dict(
                    method=method,
                    context_chars=budget,
                    questions=len(group),
                    evidence_recall=statistics.mean(
                        r["evidence_recall"] for r in group
                    ),
                    all_evidence=statistics.mean(r["all_evidence"] for r in group),
                )
            )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--ranking-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Preserve prior analysis; choose a new output")
    result = audit(args.data, args.ranking_dir)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
