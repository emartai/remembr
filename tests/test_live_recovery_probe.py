"""A logging failure must never leave owned test containers running."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.verify_shared_recovery import cleanup_services


class ProbeCleanupTests(unittest.TestCase):
    def test_logging_failure_still_stops_every_owned_service_before_database_drop(self):
        calls = []

        def command(*args):
            calls.append(args)
            if args[1] == "logs":
                raise UnicodeError("simulated Windows decoding failure")
            return ""

        with tempfile.TemporaryDirectory() as directory:
            with patch("benchmarks.verify_shared_recovery.run", side_effect=command):
                errors = cleanup_services(
                    ["owned-redis", "owned-api"], "owned-db", True, Path(directory)
                )
        self.assertEqual(errors, [])
        self.assertIn(("docker", "stop", "owned-api"), calls)
        self.assertIn(("docker", "stop", "owned-redis"), calls)
        self.assertEqual(
            calls[-1],
            (
                "docker",
                "exec",
                "remembr-postgres",
                "dropdb",
                "-U",
                "remembr",
                "owned-db",
            ),
        )

    def test_database_not_created_by_probe_is_never_dropped(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("benchmarks.verify_shared_recovery.run") as command:
                cleanup_services([], "existing-database", False, Path(directory))
                command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
