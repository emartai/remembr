"""Setup must preserve user configuration across repeated runs."""

import importlib.util
import io
import tempfile
import unittest
from http.client import RemoteDisconnected
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "local_setup", Path(__file__).resolve().parents[1] / "scripts/local_setup.py"
)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class LocalSetupTests(unittest.TestCase):
    def test_startup_connection_close_is_retried_until_ready(self):
        settings = {
            "EMBEDDING_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://host.docker.internal:11434",
        }
        with (
            patch.object(setup, "prepare_env", return_value=settings),
            patch.object(setup.subprocess, "run"),
            patch.object(setup.time, "sleep"),
            patch.object(
                setup,
                "urlopen",
                side_effect=[
                    RemoteDisconnected("starting"),
                    io.BytesIO(b'{"data":{"status":"ready"}}'),
                ],
            ),
            patch("sys.argv", ["local_setup.py", "--timeout", "10"]),
        ):
            self.assertEqual(setup.main(), 0)

    def test_first_setup_generates_secret_and_repeated_setup_preserves_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env.example").write_text(
                "SECRET_KEY=change-me-in-production\nEMBEDDING_PROVIDER=ollama\n",
                encoding="utf-8",
            )
            with (
                patch.object(setup, "ROOT", root),
                patch.dict(setup.os.environ, {}, clear=True),
            ):
                setup.prepare_env()
                original = (root / ".env").read_text(encoding="utf-8")
                self.assertNotIn("change-me-in-production", original)
                self.assertGreater(len(original.split("SECRET_KEY=")[1].strip()), 32)
                setup.prepare_env()
                self.assertEqual((root / ".env").read_text(encoding="utf-8"), original)

    def test_existing_secret_and_provider_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = "SECRET_KEY=existing-user-secret\nEMBEDDING_PROVIDER=jina\n"
            (root / ".env").write_text(original, encoding="utf-8")
            with (
                patch.object(setup, "ROOT", root),
                patch.dict(setup.os.environ, {}, clear=True),
            ):
                settings = setup.prepare_env()
                self.assertEqual(settings["EMBEDDING_PROVIDER"], "jina")
                self.assertEqual((root / ".env").read_text(encoding="utf-8"), original)

    def test_environment_provider_override_matches_compose_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "SECRET_KEY=existing\nEMBEDDING_PROVIDER=ollama\n", encoding="utf-8"
            )
            with (
                patch.object(setup, "ROOT", root),
                patch.dict(
                    setup.os.environ, {"EMBEDDING_PROVIDER": "openai"}, clear=True
                ),
            ):
                self.assertEqual(setup.prepare_env()["EMBEDDING_PROVIDER"], "openai")


if __name__ == "__main__":
    unittest.main()
