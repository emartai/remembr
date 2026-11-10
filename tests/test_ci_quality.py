"""The public CI artifact must contain only aggregate, allowlisted results."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.ci_quality import export


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


if __name__ == "__main__":
    unittest.main()
