"""Local scoring must preserve model identity and failure denominators."""

import json
import tempfile
import unittest
from benchmarks.local_answer_pilot import calibrate_judge
from pathlib import Path
from unittest.mock import patch

from benchmarks.local_answer_pilot import (
    OPTIONS,
    append,
    judge_messages,
    summarize,
    verify_models,
)


class LocalAnswerPilotTests(unittest.TestCase):
    def test_judge_payload_is_blind_to_candidate_variant(self):
        messages = judge_messages("question", "reference", "answer", False)
        payload = json.loads(messages[1]["content"])
        self.assertEqual(
            set(payload), {"question", "reference", "answer", "unanswerable"}
        )

    def test_changed_weights_and_generation_options_are_rejected(self):
        class Http:
            def call(self, *args):
                return {
                    "models": [
                        {"name": "reader", "digest": "changed"},
                        {"name": "judge", "digest": "judge-digest"},
                    ]
                }

        manifest = {
            "options": dict(OPTIONS),
            "reader": {"name": "reader", "digest": "reader-digest"},
            "judge": {"name": "judge", "digest": "judge-digest"},
        }
        with self.assertRaises(ValueError):
            verify_models(Http(), manifest)
        manifest["options"]["num_ctx"] = 8192
        with self.assertRaises(ValueError):
            verify_models(Http(), manifest)

    def test_invalid_judgment_and_missing_answers_remain_in_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for index in range(3):
                append(work / "cases.jsonl", {"variant": "baseline"})
            append(
                work / "answers.jsonl", {"variant": "baseline", "error": "TimeoutError"}
            )
            append(work / "judgments.jsonl", {"variant": "baseline", "correct": True})
            append(work / "judgments.jsonl", {"variant": "baseline", "correct": None})
            with patch("builtins.print"):
                summarize(work)
            report = json.loads((work / "summary.json").read_text())
            self.assertFalse(report["judge_sanity_passed"])
            self.assertAlmostEqual(
                report["variants"]["baseline"]["correct_fraction_all_expected"], 1 / 3
            )
            self.assertEqual(report["variants"]["baseline"]["invalid_judgments"], 1)
            self.assertEqual(report["variants"]["baseline"]["reader_errors"], 1)

    def test_always_false_judge_is_rejected_before_any_dataset_grading(self):
        class Http:
            def call(self, method, path, body=None):
                return (
                    {"models": [{"name": "judge", "digest": "frozen"}]}
                    if path == "/api/tags"
                    else {}
                )

        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            with patch(
                "benchmarks.local_answer_pilot.complete",
                return_value={"text": '{"correct":false}'},
            ):
                with self.assertRaises(RuntimeError):
                    calibrate_judge(work, Http(), "judge")
            self.assertFalse((work / "judgments.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
