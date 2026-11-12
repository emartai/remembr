"""Offline Nomic task-prefix ablation; this is not Remembr API latency or QA accuracy."""

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

from benchmarks.locomo import (
    Http,
    chunks,
    evidence_metrics,
    read_json,
    state_paths,
    visible_turns,
    write_json,
)


def cosine(left, right):
    norm = math.sqrt(sum(x * x for x in left) * sum(x * x for x in right))
    return sum(a * b for a, b in zip(left, right, strict=True)) / norm if norm else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--model", default="nomic-embed-text:publisher-f16")
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    manifest = read_json(work / "manifest.json")["config"]
    samples = [
        s
        for s in read_json(work / "locomo10.json")
        if str(s["sample_id"]) in manifest["sample_ids"]
    ]
    questions = [
        json.loads(line)
        for line in (work / "retrieval.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    documents = {
        str(s["sample_id"]): chunks(s, manifest["turns_per_chunk"]) for s in samples
    }
    http = Http("http://127.0.0.1:11434", interval=0, timeout=120)
    model = next(
        m for m in http.call("GET", "/api/tags")["models"] if m["name"] == args.model
    )
    cache_path = work / "embedding-ablation-vectors.json"
    cache = read_json(cache_path) if cache_path.exists() else {}

    def embed(text):
        key = hashlib.sha256((model["digest"] + "\n" + text).encode()).hexdigest()
        if key not in cache:
            cache[key] = http.call(
                "POST", "/api/embeddings", {"model": args.model, "prompt": text}
            )["embedding"]
            write_json(cache_path, cache)
        return cache[key]

    results = []
    for prefix in (False, True):
        vectors = {}
        for sid, docs in documents.items():
            vectors[sid] = [
                embed(("search_document: " if prefix else "") + d["content"])
                for d in docs
            ]
        for top_k in (manifest["top_k"], 16):
            scores = []
            for question in questions:
                if (
                    question.get("error")
                    or question["category"] == 5
                    or not question["evidence"]
                ):
                    continue
                query = embed(
                    ("search_query: " if prefix else "") + question["question"]
                )
                sid = question["sample_id"]
                ordered = sorted(
                    range(len(vectors[sid])),
                    key=lambda i: cosine(query, vectors[sid][i]),
                    reverse=True,
                )
                remaining, visible = manifest["context_chars"], set()
                for index in ordered[:top_k]:
                    doc = documents[sid][index]
                    visible |= visible_turns(
                        {
                            "content": doc["content"][:remaining],
                            "content_truncated": len(doc["content"]) > remaining,
                        }
                    )
                    remaining -= min(remaining, len(doc["content"]))
                    if remaining == 0:
                        break
                scores.append(evidence_metrics(set(question["evidence"]), visible))
            result = {
                "task_prefixes": prefix,
                "top_k": top_k,
                "evidence_questions": len(scores),
                "mean_evidence_recall": statistics.mean(
                    s["evidence_recall"] for s in scores
                ),
                "all_evidence": statistics.mean(s["all_evidence"] for s in scores),
            }
            results.append(result)
            print(json.dumps(result), flush=True)
    write_json(
        work / "embedding-ablation.json",
        {
            "model": model,
            "results": results,
            "scope": "Development pilot, offline cosine retrieval only; not API latency, judged accuracy or a competitor comparison",
            "source": "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5#task-instruction-prefixes",
        },
    )


if __name__ == "__main__":
    main()
