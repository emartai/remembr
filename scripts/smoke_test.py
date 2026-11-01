"""Verify a live local Remembr pipeline without third-party Python dependencies."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url", default=os.getenv("REMEMBR_URL", "http://localhost:8000")
    )
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    base = args.url.rstrip("/") + "/api/v1"

    def call(method, path, body=None, key=None, token=None, expected=200):
        headers = {"Content-Type": "application/json"}
        if key:
            headers["X-API-Key"] = key
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            base + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=45 if path == "/ready" else 30) as response:
                status, payload = response.status, json.load(response)
        except HTTPError as exc:
            status, payload = exc.code, json.load(exc)
        if status != expected:
            code = payload.get("error", {}).get("code", "unknown")
            raise RuntimeError(
                f"{method} {path}: expected {expected}, got {status} ({code})"
            )
        return payload.get("data", {})

    def identity():
        nonce = secrets.token_hex(10)
        auth = call(
            "POST",
            "/auth/register",
            {
                "email": f"smoke-{nonce}@example.com",
                "password": secrets.token_urlsafe(24),
                "org_name": f"Remembr smoke {nonce}",
            },
            expected=201,
        )
        return call(
            "POST",
            "/api-keys",
            {"name": "local-smoke"},
            token=auth["access_token"],
            expected=201,
        )["api_key"]

    ready = call("GET", "/ready")
    if ready["status"] != "ready":
        raise RuntimeError("Memory pipeline is not ready")
    print("PASS readiness: database, migrations, Redis, worker and embeddings")
    key, other_key = identity(), identity()
    session = call(
        "POST",
        "/sessions",
        {"metadata": {"source": "local-smoke"}},
        key=key,
        expected=201,
    )["session_id"]
    content = f"Remembr smoke decision {secrets.token_hex(12)}: use PostgreSQL for project memory."
    episode = call(
        "POST",
        "/memory",
        {
            "content": content,
            "role": "assistant",
            "session_id": session,
            "tags": ["local-smoke", "kind:decision"],
        },
        key=key,
        expected=201,
    )["episode_id"]
    status_path = f"/memory/{episode}/status"
    deadline = time.monotonic() + args.timeout
    try:
        while True:
            status = call("GET", status_path, key=key)
            if status["embedding_status"] == "ready":
                break
            if status["embedding_status"] == "failed":
                raise RuntimeError("Embedding failed; inspect worker logs")
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    "Embedding stayed pending; inspect worker and broker logs"
                )
            time.sleep(1)
        search = {
            "query": content,
            "session_id": session,
            "role": "assistant",
            "tags": ["local-smoke"],
            "tag_filters": [{"key": "kind", "op": "eq", "value": "decision"}],
            "limit": 1,
        }
        for mode in ("semantic", "keyword", "hybrid"):
            hits = call(
                "POST", "/memory/search", {**search, "search_mode": mode}, key=key
            )["results"]
            if not hits or hits[0]["episode_id"] != episode:
                raise RuntimeError(f"{mode} failed to retrieve the exact saved episode")
        call("GET", status_path, key=other_key, expected=404)
        call("DELETE", f"/memory/{episode}", key=other_key, expected=404)
        print(
            "PASS store, queued embedding, exact retrieval in all modes, tenant isolation"
        )
    finally:
        call("DELETE", f"/memory/{episode}", key=key)
    for mode in ("semantic", "keyword", "hybrid"):
        hits = call("POST", "/memory/search", {**search, "search_mode": mode}, key=key)[
            "results"
        ]
        if any(item["episode_id"] == episode for item in hits):
            raise RuntimeError(f"Deleted episode was returned by {mode}")
    call("GET", status_path, key=key, expected=404)
    print("PASS deletion: episode absent from searches and status endpoint")
    print(
        "Smoke test passed. Test accounts and session metadata remain in this local instance."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Smoke test failed: {exc}") from exc
