"""Compare three frozen retrieval methods across all ten pinned LoCoMo conversations."""

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path

from benchmarks.locomo import (
    DATASET_SHA256,
    TURN_ID,
    Http,
    chunks,
    evidence_metrics,
    state_paths,
)
from benchmarks.ranking_ablation import pack
from server.app.ranking import cosine, diversify, fuse, lexical_scores


def compare(data, model, work):
    raw = data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise ValueError("Unexpected dataset digest")
    http = Http("http://127.0.0.1:11434", interval=0, timeout=300)
    digest = next(
        m["digest"]
        for m in http.call("GET", "/api/tags")["models"]
        if m["name"] == model
    )
    protocol = dict(
        dataset_sha256=DATASET_SHA256,
        model=model,
        digest=digest,
        conversations=10,
        turns_per_chunk=8,
        max_results=8,
        context_chars=10000,
        methods=["bm25", "cosine", "rrf_mmr_compact"],
        version=1,
    )
    manifest = work / "protocol.json"
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError("Choose a fresh directory for a different protocol")
    manifest.write_text(json.dumps(protocol, indent=2))
    metrics = defaultdict(list)
    exclusions = defaultdict(int)
    samples = json.loads(raw)
    if len(samples) != protocol["conversations"]:
        raise ValueError("Unexpected conversation count")
    for ix, sample in enumerate(samples):
        checkpoint = work / f"conversation-{ix}.json"
        questions = []
        for qa in sample["qa"]:
            evidence = set(TURN_ID.findall(" ".join(qa.get("evidence", []))))
            if qa["category"] == 5:
                exclusions["adversarial"] += 1
            elif not evidence:
                exclusions["missing_evidence"] += 1
            else:
                questions.append((qa, evidence))
        if checkpoint.exists():
            rows = json.loads(checkpoint.read_text())
        else:
            documents = [c["content"] for c in chunks(sample, 8)]
            texts = ["search_document: " + doc for doc in documents]
            texts.extend("search_query: " + qa["question"] for qa, _ in questions)
            vectors = []
            for start in range(0, len(texts), 8):
                batch = texts[start : start + 8]
                result = http.call(
                    "POST", "/api/embed", {"model": model, "input": batch}
                )
                embedded = result["embeddings"]
                if len(embedded) != len(batch) or any(len(v) != 768 for v in embedded):
                    raise ValueError("Incomplete embedding batch")
                vectors.extend(embedded)
            doc_vectors = vectors[: len(documents)]
            rows = []
            for (qa, evidence), vector in zip(
                questions, vectors[len(documents) :], strict=True
            ):
                semantic = [cosine(vector, v) for v in doc_vectors]
                lexical = lexical_scores(qa["question"], documents)
                dense = sorted(range(len(documents)), key=lambda i: (-semantic[i], i))
                sparse = sorted(
                    (i for i, s in enumerate(lexical) if s > 0),
                    key=lambda i: (-lexical[i], i),
                )
                fused, scores = fuse([dense[:40], sparse[:40]])
                mixed = diversify(fused, scores, doc_vectors, 8)
                for method, order in zip(
                    protocol["methods"], (sparse, dense, mixed), strict=True
                ):
                    _, visible = pack(documents, order[:8], protocol["context_chars"])
                    rows.append(
                        dict(
                            method=method,
                            category=qa["category"],
                            **evidence_metrics(evidence, visible),
                        )
                    )
            temp = checkpoint.with_suffix(".tmp")
            temp.write_text(json.dumps(rows))
            temp.replace(checkpoint)
        if len(rows) != len(questions) * len(protocol["methods"]):
            raise ValueError("Incomplete conversation checkpoint")
        for row in rows:
            metrics[row["method"]].append(row)
        print(
            f"Completed conversation {ix + 1}/10 ({len(questions)} eligible questions)",
            flush=True,
        )
    summary = dict(
        protocol=protocol,
        exclusions=dict(exclusions),
        metrics={},
        scope="Offline annotated evidence retrieval, including previously examined conversations. Equal character ceilings. No answer accuracy, latency, or vendor comparison.",
    )
    for method, rows in metrics.items():
        multi = [r for r in rows if r["category"] == 1]
        summary["metrics"][method] = dict(
            questions=len(rows),
            multi_hop_questions=len(multi),
            evidence_recall=statistics.mean(r["evidence_recall"] for r in rows),
            all_evidence=statistics.mean(r["all_evidence"] for r in rows),
            multi_hop_recall=statistics.mean(r["evidence_recall"] for r in multi),
        )
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--model", default="nomic-embed-text:publisher-f16")
    args = parser.parse_args()
    compare(args.data, args.model, state_paths(args.work_dir))
