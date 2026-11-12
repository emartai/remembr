"""Synthetic CPU-only ranking probe; never an end-to-end API latency benchmark."""

import argparse
import hashlib
import json
import os
import platform
import random
import statistics
import time
from pathlib import Path

from benchmarks.locomo import state_paths, write_json
from server.app.ranking import rank_order


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    rng = random.Random(42)
    documents = ["project database decision " + str(i) for i in range(200)]
    vectors = [[rng.uniform(-1, 1) for _ in range(768)] for _ in documents]
    query = [rng.uniform(-1, 1) for _ in range(768)]
    timings, orders = [], []
    for _ in range(3):
        started = time.perf_counter()
        orders.append(rank_order("project database", documents, query, vectors))
        timings.append((time.perf_counter() - started) * 1000)
    if not all(order == orders[0] for order in orders):
        raise ValueError("Ranking is not deterministic")
    result = {
        "scope": __doc__,
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "candidates": 200,
        "dimensions": 768,
        "seed": 42,
        "repeats_ms": timings,
        "median_ms": statistics.median(timings),
        "order_sha256": hashlib.sha256(json.dumps(orders[0]).encode()).hexdigest(),
        "source_sha256": hashlib.sha256(
            Path(rank_order.__code__.co_filename).read_bytes()
        ).hexdigest(),
    }
    write_json(work / "performance.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
