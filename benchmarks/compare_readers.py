"""Compare installed readers on the same frozen context and citation task."""

import argparse
import json
import os
import statistics
import time
from pathlib import Path

from benchmarks.ci_quality import EMBEDDING_MODEL, JUDGE_MODEL, READER_MODEL
from benchmarks.local_answer_pilot import OPTIONS, complete, grade, jsonl
from benchmarks.locomo import (
    Http,
    TURN_ID,
    read_json,
    reader_messages,
    state_paths,
    visible_turns,
    write_json,
)

CANDIDATE = "qwen3:4b-instruct-2507-q4_K_M"
ABSTAIN = "No information available"
SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "maxItems": 4,
            "items": {"type": "string", "pattern": "^D[0-9]+:[0-9]+$"},
        },
    },
    "required": ["answer", "citations"],
    "additionalProperties": False,
}


def result_for(text, context):
    response = json.loads(text)
    answer = response["answer"].strip()
    citations = response["citations"]
    if (
        not answer
        or not isinstance(citations, list)
        or any(not isinstance(item, str) for item in citations)
    ):
        raise ValueError("Malformed reader response")
    abstained = answer.rstrip(".").casefold() == ABSTAIN.casefold()
    visible = visible_turns(
        {"content": context, "content_truncated": len(context) >= 4000}
    )
    valid = (abstained and not citations) or (
        not abstained and bool(citations) and set(citations) <= visible
    )
    return answer, set(citations), abstained, valid


def unload(http, model):
    http.call("POST", "/api/generate", {"model": model, "keep_alive": 0})


def run(work):
    frozen = read_json(work / "answers/manifest.json")
    corpus = read_json(work / "dataset/locomo10.json")
    cases = [r for r in jsonl(work / "answers/cases.jsonl") if r["variant"] == "bm25_8"]
    if not cases:
        raise ValueError("Frozen BM25 cases are missing")
    controls = jsonl(work / "answers/judge-controls.jsonl")
    http = Http("http://127.0.0.1:11434", interval=0, timeout=240)
    unload(http, EMBEDDING_MODEL)
    models = {
        row["name"]: row["digest"] for row in http.call("GET", "/api/tags")["models"]
    }
    report = {
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "source_commit": os.environ.get("GITHUB_SHA"),
        "scope": "Paired local model comparison on previously examined LoCoMo conversations; custom judge",
        "cases_sha256": frozen["cases_sha256"],
        "context_chars": frozen["reader_context_chars"],
        "options": OPTIONS,
        "questions": len(cases),
        "unanswerable": sum(r["category"] == 5 for r in cases),
        "judge": {
            "model": JUDGE_MODEL,
            "digest": models[JUDGE_MODEL],
            "passed": sum(row["passed"] for row in controls),
            "controls": len(controls),
        },
        "models": {},
    }
    if not controls or not all(row["passed"] for row in controls):
        raise ValueError("Judge calibration did not pass")
    answers = {}
    for model in (READER_MODEL, CANDIDATE):
        records = []
        try:
            for index, row in enumerate(cases):
                messages = reader_messages(row["question"], row["context"])
                messages[0]["content"] += (
                    " Return compact JSON with answer and citations. List only bare turn IDs "
                    "such as D1:2 that support the answer. If the evidence does not answer the "
                    "question, say No information available with an empty list of citations."
                )
                started = time.monotonic()
                try:
                    output = complete(http, model, messages, SCHEMA)
                    decoded = result_for(output["text"], row["context"])
                    records.append(
                        {
                            "result": decoded,
                            "seconds": time.monotonic() - started,
                            "output_limit": output["done_reason"] == "length",
                        }
                    )
                except (ValueError, TypeError, OSError, KeyError) as exc:
                    records.append(
                        {
                            "error": type(exc).__name__,
                            "seconds": time.monotonic() - started,
                        }
                    )
                print(f"{model}: reader case {index + 1}/{len(cases)}", flush=True)
            loaded = http.call("GET", "/api/ps")["models"]
            entry = next((x for x in loaded if x["name"] == model), {})
            answers[model] = records
            report["models"][model] = {
                "digest": models[model],
                "ollama_loaded_bytes": entry.get("size"),
                "ollama_vram_bytes": entry.get("size_vram"),
                "median_seconds": statistics.median(row["seconds"] for row in records),
                "first_request_seconds": records[0]["seconds"],
                "reader_errors": sum("error" in row for row in records),
                "output_limit_hits": sum(
                    row.get("output_limit", False) for row in records
                ),
            }
        finally:
            unload(http, model)
    votes = {}
    try:
        for model, records in answers.items():
            counts = dict(
                correct=0,
                guarded_correct=0,
                valid_format=0,
                correct_abstentions=0,
                unsupported_answers=0,
                cited_gold_turn=0,
                annotated_cited_answers=0,
                judge_errors=0,
            )
            votes[model] = []
            for case, record in zip(cases, records, strict=True):
                if "error" in record:
                    votes[model].append(False)
                    continue
                answer, citations, abstained, valid = record["result"]
                unknown = case["category"] == 5
                counts["valid_format"] += valid
                counts["correct_abstentions"] += unknown and abstained and valid
                counts["unsupported_answers"] += unknown and not abstained
                source = corpus[case["conversation_index"]]["qa"][case["qa_index"]]
                gold = set(TURN_ID.findall(" ".join(source.get("evidence", []))))
                if gold and not unknown and citations:
                    counts["annotated_cited_answers"] += 1
                    counts["cited_gold_turn"] += bool(citations & gold)
                try:
                    correct = grade(
                        http,
                        JUDGE_MODEL,
                        case["question"],
                        case["reference"],
                        answer,
                        unknown,
                    )
                    counts["correct"] += correct
                    counts["guarded_correct"] += correct and valid
                    votes[model].append(correct)
                except (ValueError, TypeError, OSError, KeyError):
                    counts["judge_errors"] += 1
                    votes[model].append(False)
            report["models"][model].update(counts)
        paired = list(zip(votes[READER_MODEL], votes[CANDIDATE], strict=True))
        report["paired"] = {
            "candidate_only_correct": sum(new and not old for old, new in paired),
            "baseline_only_correct": sum(old and not new for old, new in paired),
        }
    finally:
        unload(http, JUDGE_MODEL)
    public = work / "public"
    public.mkdir(exist_ok=True)
    write_json(public / "reader-comparison.json", report)
    print(json.dumps(report, indent=2), flush=True)
    if any(
        row["judge_errors"] or row["reader_errors"] == len(cases)
        for row in report["models"].values()
    ):
        raise SystemExit("Reader comparison lacks valid output or judgments")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    run(state_paths(parser.parse_args().work_dir))
