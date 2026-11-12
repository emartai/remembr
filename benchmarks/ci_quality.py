"""API-key-free quality evaluation using models inside the current CI runner."""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

from benchmarks.locomo import Http, read_json, state_paths, write_json

EMBEDDING_MODEL = "nomic-embed-text:v1.5"
READER_MODEL = "qwen3:1.7b"
JUDGE_MODEL = "qwen3:8b"


def command(*args):
    subprocess.run([sys.executable, "-m", *args], check=True)


def export(work):
    public = work / "public"
    public.mkdir(exist_ok=True)
    report = {
        "scope": "Runner-local exploratory evaluation; not official LoCoMo accuracy or a competitor ranking",
        "source_commit": os.environ.get("GITHUB_SHA"),
        "run_id": os.environ.get("GITHUB_RUN_ID"),
        "inference": "Ollama on this runner; no external LLM API",
        "stages": {},
    }
    for name, path in {
        "development": work / "ranking/development-summary.json",
        "confirmation": work / "ranking/confirmation-summary.json",
        "selection": work / "ranking/selection.json",
        "answer_pilot": work / "answers/summary.json",
        "environment": work / "environment.json",
        "cpu_ranking": work / "performance/performance.json",
    }.items():
        if path.exists():
            report["stages"][name] = read_json(path)
    report["retrieval_complete"] = all(
        name in report["stages"]
        for name in ("development", "confirmation", "selection")
    )
    answer = report["stages"].get("answer_pilot")
    control_path = work / "answers/judge-controls.jsonl"
    if control_path.exists():
        controls = [
            json.loads(line)
            for line in control_path.read_text(encoding="utf-8").splitlines()
        ]
        report["judge_calibration"] = {
            "attempted": len(controls),
            "passed": sum(r["passed"] for r in controls),
            "controls": controls,
        }
        calibration_config = work / "answers/judge-controls-config.json"
        if calibration_config.exists():
            report["judge_calibration"]["configuration"] = read_json(calibration_config)
    manifest = work / "answers/manifest.json"
    if manifest.exists():
        frozen = read_json(manifest)
        report["answer_configuration"] = {
            "reader": {k: frozen["reader"][k] for k in ("name", "digest")},
            "judge": {k: frozen["judge"][k] for k in ("name", "digest")},
            "options": frozen["options"],
            "cases_sha256": frozen["cases_sha256"],
            "reader_context_chars": frozen["reader_context_chars"],
        }
    if answer:
        report["answer_pilot_valid"] = answer["judge_sanity_passed"] and all(
            item["reader_attempts"] == item["expected_questions"]
            and item["judge_attempts"] == item["expected_questions"]
            and item["reader_errors"] == 0
            and item["invalid_judgments"] == 0
            for item in answer["variants"].values()
        )
    write_json(public / "quality-summary.json", report)
    lines = [
        "## Runner-local memory quality",
        "",
        report["scope"],
        "",
        f"Retrieval phases complete: **{report['retrieval_complete']}**.",
    ]
    if "confirmation" in report["stages"]:
        lines += [
            "",
            "| Ranker | Evidence questions | Recall | Multi-hop recall | Mean context tokens |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for variant, item in report["stages"]["confirmation"]["metrics"].items():
            lines.append(
                f"| {variant} | {item['questions']} | {item['recall']:.3f} | {item['multi_hop_recall']:.3f} | {item['mean_context_tokens']:.1f} |"
            )
    if answer:
        lines += [
            "",
            f"Judge controls: **{answer['controls_passed']}/{answer['controls_attempted']}**.",
            f"Answer pilot valid and complete: **{report['answer_pilot_valid']}**.",
            "",
            "| Ranker | Expected | Reader errors | Invalid judgments | Judged correct |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        if answer["judge_sanity_passed"]:
            for variant, item in answer["variants"].items():
                lines.append(
                    f"| {variant} | {item['expected_questions']} | {item['reader_errors']} | {item['invalid_judgments']} | {item['correct_count']} |"
                )
        else:
            lines.append(
                "Judged-correct counts withheld: the judge failed its sanity checks."
            )
    elif "judge_calibration" in report:
        calibration = report["judge_calibration"]
        lines += [
            "",
            f"Judge preflight controls: **{calibration['passed']}/{calibration['attempted']}**. No answer accuracy is available.",
        ]
    lines += [
        "",
        "Small related models and a ten-question custom rubric do not establish official accuracy. Raw cases, credentials, vectors and model weights are not included in this artifact.",
    ]
    markdown = "\n".join(lines) + "\n"
    (public / "quality-summary.md").write_text(markdown, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(markdown)
    return report


def evaluate(work, answers):
    command("benchmarks.ranking_performance", "--work-dir", str(work / "performance"))
    http = Http("http://127.0.0.1:11434", interval=0, timeout=1200)
    environment = {
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "ollama_version": http.call("GET", "/api/version")["version"],
        "models": [EMBEDDING_MODEL, READER_MODEL, JUDGE_MODEL]
        if answers
        else [EMBEDDING_MODEL],
    }
    write_json(work / "environment.json", environment)
    for model in environment["models"]:
        print(
            "Downloading public weights for runner-local inference:", model, flush=True
        )
        result = http.call("POST", "/api/pull", {"model": model, "stream": False})
        if result.get("status") != "success":
            raise RuntimeError("Local model download did not complete")
    dataset, ranking, pilot = work / "dataset", work / "ranking", work / "answers"
    if answers:
        command(
            "benchmarks.local_answer_pilot",
            "calibrate",
            "--work-dir",
            str(pilot),
            "--judge-model",
            JUDGE_MODEL,
        )
    command("benchmarks.locomo", "prepare", "--work-dir", str(dataset))
    data = dataset / "locomo10.json"
    for phase in ("development", "confirmation"):
        command(
            "benchmarks.ranking_ablation",
            "--work-dir",
            str(ranking),
            "--data",
            str(data),
            "--model",
            EMBEDDING_MODEL,
            "--phase",
            phase,
        )
    if answers:
        command(
            "benchmarks.local_answer_pilot",
            "prepare",
            "--work-dir",
            str(pilot),
            "--ranking-work-dir",
            str(ranking),
            "--data",
            str(data),
            "--reader-model",
            READER_MODEL,
            "--judge-model",
            JUDGE_MODEL,
        )
        for phase in ("answer", "judge", "summarize"):
            command("benchmarks.local_answer_pilot", phase, "--work-dir", str(pilot))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("run", "report"))
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--answers", action="store_true")
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    if args.phase == "report":
        export(work)
        return
    try:
        evaluate(work, args.answers)
    finally:
        report = export(work)
    if not report["retrieval_complete"] or (
        args.answers and not report.get("answer_pilot_valid")
    ):
        raise SystemExit(
            "Quality evaluation incomplete or contains model/judge failures; inspect the aggregate artifact"
        )
    print(
        json.dumps(
            {
                "retrieval_complete": True,
                "answer_pilot_valid": report.get("answer_pilot_valid"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
