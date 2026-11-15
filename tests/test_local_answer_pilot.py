"""Local scoring must preserve model identity and failure denominators."""

import hashlib
import json
import tempfile
import unittest
from benchmarks.local_answer_pilot import calibrate_judge
from pathlib import Path
from unittest.mock import patch

from benchmarks.local_answer_pilot import (
    OPTIONS,
    append,
    complete,
    grade,
    judge_messages,
    summarize,
    verify_models,
)
from benchmarks.locomo import reader_messages


class LocalAnswerPilotTests(unittest.TestCase):
    def test_oversized_multibyte_prompt_is_rejected_before_request(self):
        class Http:
            def call(self, *args):
                self.fail("Oversized prompt reached inference")

        with self.assertRaises(ValueError):
            complete(Http(), "qwen3:1.7b", [{"role": "user", "content": "界" * 4000}])

    def test_native_token_counts_are_required_and_window_overflow_is_rejected(self):
        class Http:
            def __init__(self, tokens):
                self.tokens = tokens

            def call(self, *args):
                return {
                    "message": {"content": "answer"},
                    "prompt_eval_count": self.tokens,
                }

        messages = [{"role": "user", "content": "question"}]
        for tokens in (None, 0, OPTIONS["num_ctx"]):
            with self.assertRaises(ValueError):
                complete(Http(tokens), "qwen3:1.7b", messages)
        result = complete(Http(20), "qwen3:1.7b", messages)
        self.assertEqual(result["prompt_tokens"], 20)
        self.assertGreater(result["prompt_token_upper_bound"], 20)

    def test_abstention_verdict_uses_only_question_and_candidate_reply(self):
        with patch("benchmarks.local_answer_pilot.complete") as complete:
            for label, expected in (
                ("gives_answer", False),
                ("abstains", True),
                ("other", False),
            ):
                complete.return_value = {"text": json.dumps({"classification": label})}
                self.assertIs(
                    grade(None, "judge", "question", "reference", "reply", True),
                    expected,
                )
                _, _, messages, schema = complete.call_args.args
                self.assertEqual(
                    json.loads(messages[1]["content"]),
                    {"question": "question", "reply": "reply"},
                )
                self.assertIn(label, schema["properties"]["classification"]["enum"])

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
            "reader_prompt_sha256": hashlib.sha256(
                json.dumps(reader_messages("question", "context")).encode()
            ).hexdigest(),
            "reader": {"name": "reader", "digest": "reader-digest"},
            "judge": {"name": "judge", "digest": "judge-digest"},
        }
        with self.assertRaises(ValueError):
            verify_models(Http(), manifest)
        manifest["options"]["num_ctx"] = 2048
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
