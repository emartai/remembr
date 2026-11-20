"""Encrypted review artifacts exclude secrets and reject tampering."""

import json
import tempfile
import unittest
from pathlib import Path

from cryptography.exceptions import InvalidTag
from benchmarks.audit_artifact import generate, seal, unseal


class AuditArtifactTests(unittest.TestCase):
    def test_round_trip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs, output = root / "inputs", root / "output"
            inputs.mkdir()
            output.mkdir()
            generate(root)
            (inputs / "answers.jsonl").write_text("PRIVATE_RESPONSE_MARKER")
            (inputs / "credentials.json").write_text("SECRET_MARKER")
            sealed = root / "audit.encrypted.json"
            seal(inputs, (root / "public-key.txt").read_text(), sealed)
            self.assertNotIn("PRIVATE_RESPONSE_MARKER", sealed.read_text())
            unseal(sealed, root / "private-key.pem", output)
            self.assertEqual(
                (output / "answers.jsonl").read_text(), "PRIVATE_RESPONSE_MARKER"
            )
            self.assertFalse((output / "credentials.json").exists())
            envelope = json.loads(sealed.read_text())
            original = envelope["nonce"]
            envelope["nonce"] = ("A" if original[0] != "A" else "B") + original[1:]
            sealed.write_text(json.dumps(envelope))
            with self.assertRaises(InvalidTag):
                unseal(sealed, root / "private-key.pem", output)


if __name__ == "__main__":
    unittest.main()
