"""Benchmark integrity tests: labels must not enter memory or reader prompts."""

import copy
import importlib.util
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "memory_benchmark", Path(__file__).resolve().parents[1] / "benchmarks/locomo.py"
)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class BenchmarkIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.sample = {
            "sample_id": "example",
            "conversation": {
                "session_2": [
                    {
                        "dia_id": "D2:1",
                        "speaker": "A",
                        "text": "Source fact",
                        "blip_caption": "A blue car",
                    }
                ],
                "session_2_date_time": "2 January",
                "session_10": [
                    {"dia_id": "D10:1", "speaker": "B", "text": "Later fact"}
                ],
            },
            "qa": [
                {
                    "question": "What?",
                    "answer": "SECRET_GOLD",
                    "evidence": ["FORBIDDEN_LABEL"],
                    "category": 1,
                }
            ],
            "observation": "FORBIDDEN_OBSERVATION",
            "event_summary": "FORBIDDEN_SUMMARY",
        }

    def test_only_source_turns_timestamps_and_captions_enter_memory(self):
        contents = "\n".join(c["content"] for c in bench.chunks(self.sample))
        for forbidden in (
            "SECRET_GOLD",
            "FORBIDDEN_LABEL",
            "FORBIDDEN_OBSERVATION",
            "FORBIDDEN_SUMMARY",
        ):
            self.assertNotIn(forbidden, contents)
        self.assertIn("2 January", contents)
        self.assertIn("A blue car", contents)
        self.assertLess(contents.index("D2:1"), contents.index("D10:1"))

    def test_reader_has_only_question_and_retrieved_context(self):
        messages = bench.reader_messages("QUESTION", "CONTEXT")
        self.assertIn("QUESTION", messages[1]["content"])
        self.assertIn("CONTEXT", messages[1]["content"])
        self.assertNotIn("SECRET_GOLD", str(messages))

    def test_selection_is_reproducible_and_independent_of_answers(self):
        sample = copy.deepcopy(self.sample)
        sample["qa"] = [
            {"question": f"Q{i}", "answer": "A", "category": i % 5 + 1}
            for i in range(50)
        ]
        first = bench.select_questions([sample], 10, 42)
        for qa in sample["qa"]:
            qa["answer"] = "CHANGED"
        second = bench.select_questions([sample], 10, 42)
        self.assertEqual(
            [q["qa_index"] for q in first], [q["qa_index"] for q in second]
        )
        self.assertEqual(len({q["category"] for q in first}), 5)

    def test_truncated_evidence_and_mentions_do_not_count_as_visible_turns(self):
        result = {
            "content": "D1:1 A: mentions D1:2\nD1:2 B: cut off",
            "content_truncated": True,
        }
        self.assertEqual(bench.visible_turns(result), {"D1:1"})

    def test_missing_gold_evidence_is_not_a_perfect_recall_score(self):
        self.assertIsNone(bench.evidence_metrics(set(), {"D1:1"})["evidence_recall"])

    def test_multi_hop_requires_every_evidence_turn(self):
        score = bench.evidence_metrics({"D1:1", "D2:2"}, {"D1:1"})
        self.assertEqual(score["evidence_recall"], 0.5)
        self.assertFalse(score["all_evidence"])

    def test_gold_free_normalized_token_score_is_not_substring_matching(self):
        self.assertEqual(bench.token_f1("The blue car", "blue car"), 1)
        self.assertLess(
            bench.token_f1("blue car and many invented details", "blue car"), 1
        )

    def test_sensitive_artifacts_cannot_be_written_inside_the_checkout(self):
        with self.assertRaises(ValueError):
            bench.state_paths(bench.ROOT / "benchmarks/raw")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                bench.state_paths(Path(directory)), Path(directory).resolve()
            )

    def test_remote_and_credential_bearing_urls_are_rejected(self):
        for url in ("https://example.com", "http://token@localhost:8000"):
            with self.assertRaises(ValueError):
                bench.ensure_local(url)

    def test_remote_models_require_explicit_opt_in_before_any_network_request(self):
        from benchmarks.providers import CompletionClient

        with patch("benchmarks.providers.request") as request:
            for provider in ("groq", "openrouter"):
                with self.assertRaises(ValueError):
                    CompletionClient(provider, "example")
            request.assert_not_called()

    def test_free_model_validation_refuses_paid_and_unknown_prices(self):
        from benchmarks.providers import validate_free_entry

        for entry in (
            {"id": "paid", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "x:free", "pricing": {}},
            {"id": "x:free", "pricing": {"prompt": "0.01", "completion": "0"}},
        ):
            with self.assertRaises(ValueError):
                validate_free_entry(entry)
        validate_free_entry(
            {"id": "x:free", "pricing": {"prompt": "0", "completion": "0"}}
        )

    def test_local_provider_rejects_credentials_before_network_request(self):
        from benchmarks.providers import CompletionClient

        with patch("benchmarks.providers.request") as request:
            with self.assertRaises(ValueError):
                CompletionClient(
                    "ollama", "qwen", ollama_url="http://secret@localhost:11434"
                )
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
