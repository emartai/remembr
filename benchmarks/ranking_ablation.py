"""Frozen, source-only local ranking experiments; never an API accuracy claim."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

from server.app.ranking import rank

from benchmarks.locomo import (
    DATASET_SHA256,
    Http,
    TURN_ID,
    chunks,
    evidence_metrics,
    read_json,
    select_questions,
    state_paths,
    visible_turns,
    write_json,
)

VARIANTS = (
    "cosine_8",
    "rrf_8",
    "mmr_8",
    "rrf_mmr_8",
    "cosine_16",
    "rrf_compact_8",
    "rrf_mmr_compact_8",
)


def pack(documents, order, budget):
    parts, visible = [], set()
    for index in order:
        if budget <= 0:
            break
        doc = documents[index]
        text = doc[:budget]
        visible |= visible_turns(
            {"content": text, "content_truncated": len(doc) > budget}
        )
        parts.append(text)
        budget -= len(text)
    return "\n\n".join(parts), visible


def aggregate(rows):
    result = {}
    for variant in VARIANTS:
        group = [r for r in rows if r["variant"] == variant]
        if not group:
            continue
        multi = [r for r in group if r["category"] == 1]
        result[variant] = {
            "questions": len(group),
            "recall": statistics.mean(r["evidence_recall"] for r in group),
            "all_evidence": statistics.mean(r["all_evidence"] for r in group),
            "multi_hop_questions": len(multi),
            "multi_hop_recall": statistics.mean(r["evidence_recall"] for r in multi)
            if multi
            else None,
            "multi_hop_all_evidence": statistics.mean(r["all_evidence"] for r in multi)
            if multi
            else None,
            "mean_context_tokens": statistics.mean(r["context_tokens"] for r in group),
        }
    return result


def choose(metrics):
    base = metrics["cosine_8"]
    eligible = [
        name
        for name, item in metrics.items()
        if name != "cosine_8"
        and item["recall"] >= base["recall"]
        and item["multi_hop_recall"] > base["multi_hop_recall"]
        and item["mean_context_tokens"] <= base["mean_context_tokens"] * 1.1
    ]
    return (
        max(
            eligible,
            key=lambda name: (
                metrics[name]["multi_hop_recall"],
                metrics[name]["all_evidence"],
                -metrics[name]["mean_context_tokens"],
            ),
        )
        if eligible
        else "cosine_8"
    )


def main():
    import tiktoken

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("development", "confirmation"), required=True
    )
    parser.add_argument("--model", default="nomic-embed-text:publisher-f16")
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    raw = args.data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise ValueError("Dataset differs from pinned LoCoMo bytes")
    samples = json.loads(raw)
    http = Http("http://127.0.0.1:11434", interval=0, timeout=120)
    model = next(
        m for m in http.call("GET", "/api/tags")["models"] if m["name"] == args.model
    )
    protocol = {
        "version": 2,
        "embedding_model": model["name"],
        "dataset_sha256": DATASET_SHA256,
        "embedding_digest": model["digest"],
        "prefixes": True,
        "turns_per_chunk": 8,
        "context_chars": 12000,
        "compact_context_chars": 10000,
        "development_indices": [0],
        "confirmation_indices": [1, 2],
        "question_selection": "all answerable questions with annotated evidence",
        "variants": VARIANTS,
        "rrf_k": 60,
        "candidate_depth": 40,
        "mmr_lambda": 0.85,
        "selection": "higher multi-hop recall, no overall recall loss, <=10% more mean tokens; choose highest multi-hop recall then all-evidence then fewer tokens",
    }
    # JSON round-trip avoids tuple/list drift when comparing frozen manifests.
    protocol = json.loads(json.dumps(protocol))
    manifest = work / "ranking-protocol.json"
    if manifest.exists() and read_json(manifest) != protocol:
        raise ValueError("Refuse changed experiment configuration")
    if not manifest.exists():
        write_json(manifest, protocol)
    output = work / (args.phase + ".jsonl")
    if output.exists():
        raise ValueError("Preserve existing results; use a new work directory")
    winner = None
    if args.phase == "confirmation":
        selection = read_json(work / "selection.json")
        dev = (work / "development.jsonl").read_bytes()
        if hashlib.sha256(dev).hexdigest() != selection["development_sha256"]:
            raise ValueError("Development results changed after selection")
        winner = selection["winner"]
    cache_path = work / "embedding-ablation-vectors.json"
    cache = read_json(cache_path) if cache_path.exists() else {}
    encoding = tiktoken.get_encoding("cl100k_base")

    def embed(text):
        key = hashlib.sha256((model["digest"] + "\n" + text).encode()).hexdigest()
        if key not in cache:
            cache[key] = http.call(
                "POST", "/api/embeddings", {"model": args.model, "prompt": text}
            )["embedding"]
            write_json(cache_path, cache)
        return cache[key]

    rows = []
    indices = protocol[args.phase + "_indices"]
    with output.open("w", encoding="utf-8") as handle:
        for index in indices:
            sample = samples[index]
            documents = [c["content"] for c in chunks(sample, 8)]
            vectors = [embed("search_document: " + d) for d in documents]
            questions = select_questions([sample], None, 42)
            for number, question in enumerate(questions):
                evidence = set(TURN_ID.findall(" ".join(question.get("evidence", []))))
                if question["category"] == 5 or not evidence:
                    continue
                rankings = rank(
                    question["question"],
                    documents,
                    embed("search_query: " + question["question"]),
                    vectors,
                )
                for variant, order in rankings.items():
                    if winner is not None and variant not in {"cosine_8", winner}:
                        continue
                    budget = (
                        protocol["compact_context_chars"]
                        if "compact" in variant
                        else protocol["context_chars"]
                    )
                    context, visible = pack(documents, order, budget)
                    row = {
                        "conversation_index": index,
                        "qa_index": question["qa_index"],
                        "category": question["category"],
                        "variant": variant,
                        "context_tokens": len(encoding.encode(context)),
                        **evidence_metrics(evidence, visible),
                    }
                    rows.append(row)
                    handle.write(json.dumps(row) + "\n")
                    handle.flush()
                if number % 20 == 0:
                    print(
                        f"Conversation {index}: question {number}/{len(questions)}",
                        flush=True,
                    )
    metrics = aggregate(rows)
    write_json(
        work / (args.phase + "-summary.json"),
        {
            "protocol": protocol,
            "metrics": metrics,
            "scope": "Offline ranking; not Remembr API latency, answer accuracy or a competitor comparison",
        },
    )
    if args.phase == "development":
        write_json(
            work / "selection.json",
            {
                "winner": choose(metrics),
                "development_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            },
        )
    print(json.dumps(metrics, indent=2), flush=True)


if __name__ == "__main__":
    main()
