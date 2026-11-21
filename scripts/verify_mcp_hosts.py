"""Run a model-free MCP handoff through the actual agent host runtimes."""

import argparse
import json
import os
import secrets
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

TOOLS = ("store_memory", "search_memory", "get_memory", "get_processing_status")
PORT = 18789
ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000"


def http(method, url, body=None, token=None, credential=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if credential:
        headers["X-API-Key"] = credential
    request = Request(
        url,
        json.dumps(body).encode() if body is not None else None,
        headers,
        method=method,
    )
    with urlopen(request, timeout=60) as response:
        return json.load(response)


def wait_for(probe, timeout=150):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            result = probe()
            if result:
                return result
        except OSError:
            pass
        time.sleep(2)
    raise TimeoutError("Expected service or memory did not become ready")


def objects(value):
    """Unwrap host JSON, MCP structuredContent and text blocks."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from objects(child)
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except ValueError:
            return
        if isinstance(parsed, (dict, list)):
            yield from objects(parsed)


def require_field(output, field):
    for record in objects(output):
        if field in record:
            return record
    raise AssertionError(f"MCP tool did not return {field}: {str(output)[:500]}")


def hermes():
    """Invoke the registered Hermes tools in its own process."""
    from tools.mcp_tool_discovery import register_mcp_servers
    from tools.registry import registry

    request = json.load(sys.stdin)
    names = register_mcp_servers({"remembr": request["server"]})
    found = {
        tool: next((name for name in names if name.endswith("_" + tool)), None)
        for tool in TOOLS
    }
    if not all(found.values()):
        raise RuntimeError(f"Hermes tool discovery incomplete: {names}")
    original = require_field(
        registry.dispatch(found["get_memory"], {"memory_id": request["original"]}),
        "source_ref",
    )
    assert original["source_ref"] == "openclaw:v1"
    stored = require_field(
        registry.dispatch(
            found["store_memory"],
            {
                "content": "The Cedar service uses PostgreSQL for its database.",
                "idempotency_key": "hermes-correction",
                "supersedes_id": original["id"],
                "source_ref": "hermes:v2",
            },
        ),
        "supersedes_id",
    )
    print("REMEMBR_MCP_RESULT=" + json.dumps(stored), flush=True)


def verify(bridge):
    if os.environ.get("COMPOSE_PROJECT_NAME") != "remembr_ci_default":
        raise RuntimeError("This fixture is restricted to the disposable CI stack")
    api = BASE + "/api/v1"
    owner = http(
        "POST",
        api + "/auth/register",
        {
            "email": "hosts-" + secrets.token_hex(8) + "@example.com",
            "password": secrets.token_urlsafe(24),
            "org_name": "Remembr MCP host verification",
        },
    )["data"]["access_token"]

    def admin(method, path, body=None):
        return http(method, api + "/projects" + path, body, token=owner)["data"]

    project = admin("POST", "", {"name": "Agent host compatibility"})
    space = admin("POST", f"/{project['id']}/spaces", {"name": "Cedar"})["id"]
    principals = {}
    for host in ("OpenClaw", "Hermes"):
        principal = admin("POST", "/principals", {"name": host})
        admin(
            "PUT",
            f"/spaces/{space}/grants/{principal['id']}",
            {"can_read": True, "can_write": True},
        )
        principals[host] = principal

    def server(host):
        return {
            "command": str(bridge),
            "args": ["-m", "remembr.mcp"],
            "env": {
                "REMEMBR_URL": BASE,
                "REMEMBR_SPACE_ID": space,
                "REMEMBR_API_KEY": principals[host]["api_key"],
            },
        }

    token = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="remembr-agent-hosts-") as temp:
        home = Path(temp)
        config = home / "openclaw.json"
        config.write_text(
            json.dumps(
                {
                    "gateway": {
                        "mode": "local",
                        "bind": "loopback",
                        "auth": {"mode": "token", "token": token},
                    },
                    "tools": {"allow": ["remembr__*"]},
                    "mcp": {"servers": {"remembr": server("OpenClaw")}},
                }
            ),
            encoding="utf-8",
        )
        config.chmod(0o600)
        env = {
            **os.environ,
            "OPENCLAW_STATE_DIR": temp,
            "OPENCLAW_CONFIG_PATH": str(config),
            "HERMES_HOME": str(home / "hermes"),
        }
        with (home / "gateway.log").open("w+", encoding="utf-8") as log:
            gateway = subprocess.Popen(
                ["openclaw", "gateway", "run", "--port", str(PORT)],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                wait_for(lambda: http("GET", f"http://127.0.0.1:{PORT}/health"))
                subprocess.run(
                    ["openclaw", "mcp", "doctor", "remembr", "--probe"],
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=True,
                )

                def openclaw(tool, arguments, field):
                    reply = http(
                        "POST",
                        f"http://127.0.0.1:{PORT}/tools/invoke",
                        {"tool": "remembr__" + tool, "args": arguments},
                        token=token,
                    )
                    assert reply["ok"]
                    return require_field(reply, field)

                original = openclaw(
                    "store_memory",
                    {
                        "content": "The Cedar service uses SQLite for its database.",
                        "source_ref": "openclaw:v1",
                        "idempotency_key": "openclaw-original",
                    },
                    "author_id",
                )
                assert original["author_id"] == principals["OpenClaw"]["id"]
                print(
                    "OpenClaw discovered the tools and stored the first decision.",
                    flush=True,
                )
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), "--hermes"],
                    input=json.dumps(
                        {"server": server("Hermes"), "original": original["id"]}
                    ),
                    env=env,
                    check=True,
                    text=True,
                    capture_output=True,
                    timeout=180,
                )
                (line,) = [
                    x
                    for x in result.stdout.splitlines()
                    if x.startswith("REMEMBR_MCP_RESULT=")
                ]
                corrected = json.loads(line.split("=", 1)[1])
                assert corrected["author_id"] == principals["Hermes"]["id"]
                assert corrected["supersedes_id"] == original["id"]
                print(
                    "Hermes discovered the tools, read the decision and saved a correction.",
                    flush=True,
                )
                subprocess.run(
                    [
                        "docker",
                        "compose",
                        "up",
                        "-d",
                        "--force-recreate",
                        "server",
                        "worker",
                    ],
                    cwd=ROOT,
                    check=True,
                    timeout=240,
                )
                wait_for(
                    lambda: http("GET", api + "/ready")["data"]["status"] == "ready"
                )
                wait_for(
                    lambda: (
                        openclaw(
                            "get_processing_status",
                            {"memory_id": corrected["id"]},
                            "embedding_status",
                        )["embedding_status"]
                        == "ready"
                    )
                )
                current = openclaw(
                    "search_memory",
                    {"query": "Cedar database", "mode": "hybrid"},
                    "results",
                )["results"]
                assert [r["id"] for r in current] == [corrected["id"]]
                assert current[0]["source_ref"] == "hermes:v2"
                admin("DELETE", f"/principals/{principals['Hermes']['id']}")
                try:
                    http(
                        "GET",
                        api + f"/projects/spaces/{space}/memories/{corrected['id']}",
                        credential=principals["Hermes"]["api_key"],
                    )
                except HTTPError as error:
                    assert error.code in (401, 403)
                else:
                    raise AssertionError("Revoked Hermes credential still works")
                assert (
                    openclaw("get_memory", {"memory_id": corrected["id"]}, "author_id")[
                        "author_id"
                    ]
                    == principals["Hermes"]["id"]
                )
                print(
                    "PASS: correction survived restart, source and authorship verified, "
                    "Hermes revocation left OpenClaw access working.",
                    flush=True,
                )
            except Exception as error:
                log.seek(0)
                diagnostic = f"{type(error).__name__}: {error}\n" + log.read()[-5000:]
                if isinstance(error, HTTPError):
                    diagnostic += error.read().decode(errors="replace")[-2500:]
                if isinstance(error, subprocess.CalledProcessError):
                    diagnostic += (error.stderr or "")[-2500:]
                for secret in [
                    token,
                    owner,
                    *[p["api_key"] for p in principals.values()],
                ]:
                    diagnostic = diagnostic.replace(secret, "[redacted]")
                print(diagnostic, file=sys.stderr)
                raise RuntimeError(
                    f"Host probe failed: {type(error).__name__}"
                ) from None
            finally:
                gateway.terminate()
                try:
                    gateway.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    gateway.kill()
                    gateway.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--hermes", action="store_true")
    args = parser.parse_args()
    if args.hermes:
        hermes()
    else:
        verify(args.bridge.resolve(strict=True))
