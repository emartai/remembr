"""Start the local stack. Requires Python 3.11+ and Docker Compose v2."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]


def prepare_env() -> dict[str, str]:
    path = ROOT / ".env"
    content = (
        path.read_text(encoding="utf-8")
        if path.exists()
        else (ROOT / ".env.example").read_text(encoding="utf-8")
    )
    values = {}
    for line in content.splitlines():
        if line.strip() and not line.lstrip().startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"'")
    if values.get("SECRET_KEY") in (None, "", "change-me-in-production"):
        secret = secrets.token_urlsafe(48)
        lines = [
            line for line in content.splitlines() if not line.startswith("SECRET_KEY=")
        ]
        content = "\n".join(lines) + f"\nSECRET_KEY={secret}\n"
    if not path.exists() or content != path.read_text(encoding="utf-8"):
        path.write_text(content, encoding="utf-8")
    return {**values, **os.environ}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout", type=int, default=300, help="Readiness timeout in seconds"
    )
    parser.add_argument(
        "--skip-ollama-bootstrap",
        action="store_true",
        help="Use an already configured Ollama service/model; still verify inference readiness",
    )
    args = parser.parse_args()
    settings = prepare_env()
    compose_executable = settings.get("DOCKER_COMPOSE_EXE")

    def docker(*arguments, timeout=3600):
        command = ["docker", *arguments]
        if compose_executable and arguments[0] == "compose":
            command = [compose_executable, *arguments[1:]]
        subprocess.run(command, cwd=ROOT, check=True, timeout=timeout)

    try:
        print("Validating Compose configuration...", flush=True)
        docker("compose", "config", "--quiet", timeout=60)
        print("Starting storage and checking its port bindings...", flush=True)
        docker("compose", "up", "-d", "postgres", "redis", "pgbouncer", timeout=180)
        provider = settings.get("EMBEDDING_PROVIDER", "ollama")
        bundled_ollama = (
            urlparse(settings.get("OLLAMA_BASE_URL", "http://ollama:11434")).hostname
            == "ollama"
        )
        if provider == "ollama" and bundled_ollama and not args.skip_ollama_bootstrap:
            print(
                "Starting local Ollama and downloading the configured embedding model...",
                flush=True,
            )
            docker("compose", "--profile", "ollama", "run", "--rm", "ollama-init")
        elif provider == "ollama":
            print(
                "Using the configured existing Ollama service; readiness will verify inference.",
                flush=True,
            )
        print(
            "Building and starting storage, migrations, API, worker and scheduler...",
            flush=True,
        )
        docker("compose", "up", "-d", "--build")
        url = settings.get(
            "REMEMBR_URL", f"http://localhost:{settings.get('REMEMBR_PORT', '8000')}"
        ).rstrip("/")
        deadline = time.monotonic() + args.timeout
        checks = {}
        while time.monotonic() < deadline:
            try:
                with urlopen(f"{url}/api/v1/ready", timeout=45) as response:
                    payload = json.load(response)["data"]
                    if payload.get("status") == "ready":
                        print(
                            f"Ready: {url}/api/v1. Next: python scripts/smoke_test.py",
                            flush=True,
                        )
                        return 0
            except HTTPError as exc:
                try:
                    checks = json.load(exc).get("data", {}).get("checks", {})
                except (ValueError, KeyError):
                    pass
            except (URLError, TimeoutError, ConnectionError, json.JSONDecodeError):
                pass
            time.sleep(3)
        raise RuntimeError(
            f"Readiness timed out; component status: {checks}. Run docker compose logs server worker migrate."
        )
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        print(f"Setup failed: {exc}", flush=True)
        print(
            "Check the command above and docs/local-setup.md. Existing data has been retained."
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
