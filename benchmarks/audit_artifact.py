"""Encrypt benchmark responses for a reviewer whose private key stays off CI."""

import argparse
import base64
import io
import json
import os
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from benchmarks.locomo import state_paths

FILES = (
    "cases.jsonl",
    "answers.jsonl",
    "judgments.jsonl",
    "manifest.json",
    "judge-controls.jsonl",
    "judge-controls-config.json",
    "summary.json",
)
LABEL = b"remembr-benchmark-audit-v1"


def oaep():
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=LABEL,
    )


def generate(work):
    private_path = work / "private-key.pem"
    if private_path.exists():
        raise ValueError("Preserve the existing review key")
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    private_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    public = key.public_key().public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    (work / "public-key.txt").write_text(
        base64.b64encode(public).decode(), encoding="ascii"
    )
    print("Review keys written outside checkout. Keep private-key.pem on this machine.")


def seal(work, public_key, output):
    key = serialization.load_der_public_key(base64.b64decode(public_key, validate=True))
    if not isinstance(key, rsa.RSAPublicKey) or key.key_size < 3072:
        raise ValueError("An RSA public key of at least 3072 bits is required")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            path = work / name
            if path.exists():
                archive.writestr(name, path.read_bytes())
    session_key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
    envelope = {
        "version": 1,
        "wrapped_key": base64.b64encode(key.encrypt(session_key, oaep())).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(
            AESGCM(session_key).encrypt(nonce, buffer.getvalue(), LABEL)
        ).decode(),
    }
    output.write_text(json.dumps(envelope), encoding="utf-8")
    print("Encrypted audit artifact written; raw responses remain sealed.")


def unseal(source, private_path, work):
    envelope = json.loads(source.read_text(encoding="utf-8"))
    if envelope["version"] != 1:
        raise ValueError("Unknown encrypted audit format")
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    session_key = key.decrypt(base64.b64decode(envelope["wrapped_key"]), oaep())
    plaintext = AESGCM(session_key).decrypt(
        base64.b64decode(envelope["nonce"]),
        base64.b64decode(envelope["ciphertext"]),
        LABEL,
    )
    with zipfile.ZipFile(io.BytesIO(plaintext)) as archive:
        if any(info.filename not in FILES for info in archive.infolist()):
            raise ValueError("Unexpected audit archive entry")
        for info in archive.infolist():
            destination = work / info.filename
            if destination.exists():
                raise ValueError(
                    "Preserve existing audit files; choose a fresh directory"
                )
        for info in archive.infolist():
            (work / info.filename).write_bytes(archive.read(info))
    print("Audit decrypted outside checkout for review.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("keygen", "seal", "unseal"))
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--private-key", type=Path)
    args = parser.parse_args()
    work = state_paths(args.work_dir)
    if args.phase == "keygen":
        generate(work)
    elif args.phase == "seal":
        if not args.output:
            parser.error("seal requires --output")
        seal(work, os.environ["BENCHMARK_AUDIT_PUBLIC_KEY"], args.output)
    else:
        if not args.source or not args.private_key:
            parser.error("unseal requires --source and --private-key")
        unseal(args.source, args.private_key, work)


if __name__ == "__main__":
    main()
