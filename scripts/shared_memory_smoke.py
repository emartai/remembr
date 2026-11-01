"""Live graph/SDK/MCP acceptance with independent credentials and synthetic data.

Requires the repository Python SDK plus MCP extra in this interpreter, and LangGraph
in --graph-python's environment. Account metadata remains; memory content is deleted.
"""

import argparse
import json
import os
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--graph-python", default=sys.executable)
    parser.add_argument("--output")
    args = parser.parse_args()
    base = os.getenv("REMEMBR_URL", "http://localhost:8000").rstrip("/")
    if not base.endswith("/api/v1"):
        base += "/api/v1"

    def api(method, path, body=None, token=None, key=None, expect=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        if key:
            headers["X-API-Key"] = key
        request = Request(
            base + path,
            method=method,
            headers=headers,
            data=json.dumps(body).encode() if body is not None else None,
        )
        try:
            with urlopen(request, timeout=60) as response:
                data = json.load(response)["data"]
            assert expect is None, "Expected access denial"
            return data
        except HTTPError as exc:
            if expect == exc.code:
                return None
            raise RuntimeError(
                f"HTTP {exc.code} at {path}: {exc.read().decode()[:400]}"
            ) from exc

    deadline = time.monotonic() + 300
    while True:
        try:
            if api("GET", "/ready")["status"] == "ready":
                break
        except (OSError, RuntimeError):
            pass
        if time.monotonic() > deadline:
            raise TimeoutError("Local stack did not become ready")
        time.sleep(3)
    print("PASS dependency readiness", flush=True)
    unique = uuid.uuid4().hex
    account = api(
        "POST",
        "/auth/register",
        {
            "email": f"shared-{unique}@example.com",
            "password": secrets.token_urlsafe(24),
            "org_name": "Synthetic shared-memory acceptance",
        },
    )
    owner = account["access_token"]

    def admin(method, path, body=None):
        return api(method, "/projects" + path, body, token=owner)

    project = admin("POST", "", {"name": "Synthetic product " + unique[:8]})
    space = admin("POST", f"/{project['id']}/spaces", {"name": "Decisions"})
    principals = [
        admin("POST", "/principals", {"name": name})
        for name in (
            "LangGraph writer",
            "MCP correction client",
            "MCP recall client",
            "Read only",
            "Ungrant",
        )
    ]
    for i, p in enumerate(principals[:4]):
        admin(
            "PUT",
            f"/spaces/{space['id']}/grants/{p['id']}",
            {"can_read": True, "can_write": i < 3},
        )
    common = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "sdk/python"),
        "REMEMBR_SPACE_ID": space["id"],
        "REMEMBR_URL": base.removesuffix("/api/v1"),
    }

    def child(interpreter, file, principal, extra):
        run = subprocess.run(
            [interpreter, str(ROOT / "examples/shared-project-memory" / file)],
            check=False,
            env={**common, "REMEMBR_API_KEY": principal["api_key"], **extra},
            capture_output=True,
            text=True,
            timeout=600,
        )
        if run.returncode:
            raise RuntimeError(run.stderr[-2500:])
        return json.loads(run.stdout.splitlines()[-1])

    marker = "synthetic-" + unique
    finding = (
        marker
        + ": prototype storage is PostgreSQL. Reference code "
        + secrets.token_hex(8)
    )
    original = child(
        args.graph_python,
        "langgraph_writer.py",
        principals[0],
        {"REMEMBR_DEMO_KEY": "research-1", "REMEMBR_DEMO_FINDING": finding},
    )
    print("PASS independent LangGraph write", flush=True)
    correction_text = (
        marker
        + ": correction: prototype storage is SQLite. Reference code "
        + secrets.token_hex(8)
    )
    corrected = child(
        sys.executable,
        "mcp_client.py",
        principals[1],
        {
            "REMEMBR_DEMO_QUERY": marker,
            "REMEMBR_DEMO_ACTION": "correct",
            "REMEMBR_DEMO_CORRECTION": correction_text,
            "REMEMBR_DEMO_KEY": "correction-1",
        },
    )
    recalled = child(
        sys.executable, "mcp_client.py", principals[2], {"REMEMBR_DEMO_QUERY": marker}
    )
    print("PASS fresh MCP correction and recall processes", flush=True)
    assert recalled["results"][0]["id"] == corrected["id"]
    assert recalled["results"][0]["content"] == correction_text
    assert recalled["results"][0]["author_id"] == principals[1]["id"]
    assert corrected["supersedes_id"] == original["memory_id"]
    original_path = f"/projects/spaces/{space['id']}/memories/{original['memory_id']}"
    old = api("GET", original_path, key=principals[2]["api_key"])
    assert old["state"] == "superseded" and old["content"] == finding
    search_path = f"/projects/spaces/{space['id']}/search"
    api("POST", search_path, {}, key=principals[4]["api_key"], expect=404)
    api(
        "POST",
        f"/projects/spaces/{space['id']}/memories",
        {"content": "forbidden", "idempotency_key": "deny"},
        key=principals[3]["api_key"],
        expect=404,
    )
    admin("DELETE", f"/principals/{principals[3]['id']}")
    api("POST", search_path, {}, key=principals[3]["api_key"], expect=401)
    deadline = time.monotonic() + 180
    while True:
        status = api(
            "GET",
            f"/projects/spaces/{space['id']}/memories/{corrected['id']}/status",
            key=principals[2]["api_key"],
        )
        if status["embedding_status"] == "ready":
            break
        if status["embedding_status"] == "failed" or time.monotonic() > deadline:
            raise RuntimeError("Embedding did not become ready: " + json.dumps(status))
        time.sleep(2)
    for mode in ("keyword", "semantic", "hybrid"):
        found = api(
            "POST",
            search_path,
            {"query": marker, "mode": mode},
            key=principals[2]["api_key"],
        )
        assert found["results"][0]["id"] == corrected["id"], mode
    for memory_id in (original["memory_id"], corrected["id"]):
        admin("DELETE", f"/spaces/{space['id']}/memories/{memory_id}")
    assert not api("POST", search_path, {}, key=principals[2]["api_key"])["results"]
    for principal in principals:
        admin("DELETE", f"/principals/{principal['id']}")
    evidence = {
        "result": "passed",
        "langgraph_independent_process": True,
        "fresh_mcp_processes": 2,
        "distinct_principals": 3,
        "correction_lineage": True,
        "authenticated_authorship": True,
        "read_only_ungranted_revoked_checks": True,
        "search_modes": ["keyword", "semantic", "hybrid"],
        "local_embedding_ready": True,
        "memory_content_deleted": True,
        "credentials_revoked": True,
        "claude_code_model_session": False,
        "codex_model_session": False,
        "note": "Actual graph and MCP protocol processes; host model sessions are separate checks.",
    }
    if args.output:
        Path(args.output).write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
