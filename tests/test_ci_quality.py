"""The public CI artifact must contain only aggregate, allowlisted results."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.ci_quality import export, evaluate


class QualityArtifactTests(unittest.TestCase):
    def test_raw_data_and_credentials_are_not_published(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            (work / "private-credentials.json").write_text('{"key":"SECRET_MARKER"}')
            (work / "cases.jsonl").write_text('{"answer":"RAW_ANSWER_MARKER"}')
            with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": ""}):
                report = export(work)
            public = list((work / "public").iterdir())
            self.assertEqual(
                {p.name for p in public}, {"quality-summary.json", "quality-summary.md"}
            )
            for path in public:
                value = path.read_text()
                self.assertNotIn("SECRET_MARKER", value)
                self.assertNotIn("RAW_ANSWER_MARKER", value)
            self.assertFalse(report["retrieval_complete"])

    def test_calibration_precedes_dataset_and_reader_and_flags_reach_correct_cli(self):
        class Http:
            def call(self, method, path, body=None):
                return (
                    {"version": "test"}
                    if path == "/api/version"
                    else {"status": "success"}
                )

        calls = []
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch("benchmarks.ci_quality.Http", return_value=Http()),
                patch(
                    "benchmarks.ci_quality.command",
                    side_effect=lambda *args: calls.append(args),
                ),
            ):
                evaluate(Path(directory), True)
        calibration = next(i for i, args in enumerate(calls) if "calibrate" in args)
        dataset = next(
            i for i, args in enumerate(calls) if args[0] == "benchmarks.locomo"
        )
        reader = next(
            i
            for i, args in enumerate(calls)
            if args[0] == "benchmarks.local_answer_pilot" and "answer" in args
        )
        self.assertLess(calibration, dataset)
        self.assertLess(calibration, reader)
        for args in calls:
            if args[0] == "benchmarks.ranking_ablation":
                self.assertNotIn("--judge-model", args)
                self.assertNotIn("--reader-model", args)
        prepare = next(
            args
            for args in calls
            if args[0] == "benchmarks.local_answer_pilot" and "prepare" in args
        )
        self.assertIn("--judge-model", prepare)
        self.assertIn("qwen3:8b", prepare)

    def test_failed_preflight_never_runs_reader_or_retrieval(self):
        class Http:
            def call(self, method, path, body=None):
                return (
                    {"version": "test"}
                    if path == "/api/version"
                    else {"status": "success"}
                )

        calls = []

        def command(*args):
            calls.append(args)
            if "calibrate" in args:
                raise RuntimeError("Unreliable judge")

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch("benchmarks.ci_quality.Http", return_value=Http()),
                patch("benchmarks.ci_quality.command", side_effect=command),
            ):
                with self.assertRaises(RuntimeError):
                    evaluate(Path(directory), True)
        self.assertFalse(
            any(
                args[0] == "benchmarks.ranking_ablation" or "answer" in args
                for args in calls
            )
        )


if __name__ == "__main__":
    unittest.main()
