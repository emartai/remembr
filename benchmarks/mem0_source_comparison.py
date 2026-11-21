"""Evaluate Mem0's source-storage mode with the same cached local vectors."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import statistics
import threading
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from benchmarks.locomo import DATASET_SHA256, TURN_ID, chunks, evidence_metrics
from benchmarks.ranking_ablation import pack
from server.app.ranking import lexical_scores, rank


def run(data, ranking_dir, work):
    raw = data.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATASET_SHA256:
        raise ValueError("Unexpected dataset")
    if work.exists():
        raise ValueError("Choose a new work directory")
    work.mkdir(parents=True)
    os.environ["MEM0_TELEMETRY"] = "false"
    os.environ["MEM0_DIR"] = str(work / "mem0-home")
    from mem0 import Memory

    protocol = json.loads((ranking_dir / "ranking-protocol.json").read_text())
    cache = json.loads((ranking_dir / "embedding-ablation-vectors.json").read_text())
    digest = protocol["embedding_digest"]
    samples = json.loads(raw)
    lookup = {}
    for index in protocol["confirmation_indices"]:
        sample = samples[index]
        for doc in chunks(sample, 8):
            text = doc["content"]
            key = hashlib.sha256(
                (digest + "\nsearch_document: " + text).encode()
            ).hexdigest()
            lookup[text] = cache[key]
        for qa in sample["qa"]:
            key = hashlib.sha256(
                (digest + "\nsearch_query: " + qa["question"]).encode()
            ).hexdigest()
            if key in cache:
                lookup[qa["question"]] = cache[key]
                lookup.setdefault(qa["question"].strip(), cache[key])
    requests = defaultdict(int)

    class CachedVectors(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, body, status=200):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())

        def do_GET(self):
            requests[self.path] += 1
            if self.path == "/api/tags":
                self.reply(
                    {
                        "models": [
                            {
                                "name": "cached-nomic:latest",
                                "model": "cached-nomic:latest",
                            }
                        ]
                    }
                )
            else:
                self.reply({"error": "Disabled endpoint"}, 400)

        def do_POST(self):
            requests[self.path] += 1
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/api/embed":
                texts = body["input"]
                texts = [texts] if isinstance(texts, str) else texts
                if all(text in lookup for text in texts):
                    self.reply({"embeddings": [lookup[text] for text in texts]})
                    return
            self.reply({"error": "Uncached request or generation disabled"}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", 0), CachedVectors)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}"
    config = {
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "cached-nomic:latest",
                "embedding_dims": 768,
                "ollama_base_url": url,
            },
        },
        "llm": {
            "provider": "ollama",
            "config": {"model": "disabled", "ollama_base_url": url},
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "source_comparison",
                "embedding_model_dims": 768,
                "path": str(work / "qdrant"),
            },
        },
        "history_db_path": str(work / "history.db"),
    }
    rows = []
    try:
        memory = Memory.from_config(config)
        for index in protocol["confirmation_indices"]:
            sample = samples[index]
            docs = [c["content"] for c in chunks(sample, 8)]
            user = f"conversation-{index}"
            for doc in docs:
                memory.add(doc, user_id=user, infer=False)
            for qa in sample["qa"]:
                evidence = set(TURN_ID.findall(" ".join(qa.get("evidence", []))))
                if qa["category"] == 5 or not evidence:
                    continue
                found = memory.search(
                    qa["question"], filters={"user_id": user}, limit=8
                )
                source_results = [r["memory"] for r in found["results"]]
                if any(text not in docs for text in source_results):
                    raise ValueError(
                        "Unexpected cross-conversation or transformed source"
                    )
                rankings = rank(
                    qa["question"],
                    docs,
                    lookup[qa["question"]],
                    [lookup[d] for d in docs],
                )
                scores = lexical_scores(qa["question"], docs)
                rankings["bm25"] = sorted(
                    (i for i, s in enumerate(scores) if s > 0),
                    key=lambda i: (-scores[i], i),
                )[:8]
                for method in ("mem0_source", "cosine_8", "bm25", "rrf_mmr_compact_8"):
                    sources = (
                        source_results
                        if method == "mem0_source"
                        else [docs[i] for i in rankings[method]]
                    )
                    for budget in (4000, 10000):
                        _, visible = pack(sources, list(range(len(sources))), budget)
                        rows.append(
                            dict(
                                method=method,
                                budget=budget,
                                category=qa["category"],
                                **evidence_metrics(evidence, visible),
                            )
                        )
            print(f"Completed conversation {index}", flush=True)
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    if any(path not in ("/api/tags", "/api/embed") for path in requests):
        raise ValueError("Unexpected model endpoint used")
    summary = {
        "scope": "Mem0 source-storage mode (infer=False), same cached Nomic vectors and raw chunks. Fact extraction disabled. Offline evidence retrieval only. Previously evaluated conversations 1 and 2.",
        "packages": {
            p: importlib.metadata.version(p)
            for p in ("mem0ai", "qdrant-client", "ollama")
        },
        "dataset_sha256": DATASET_SHA256,
        "embedding_digest": digest,
        "local_adapter_requests": dict(requests),
        "metrics": [],
    }
    for method in ("mem0_source", "cosine_8", "bm25", "rrf_mmr_compact_8"):
        for budget in (4000, 10000):
            group = [r for r in rows if r["method"] == method and r["budget"] == budget]
            summary["metrics"].append(
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
    (work / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--ranking-dir", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.data, args.ranking_dir, args.work_dir)
