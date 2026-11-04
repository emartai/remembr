"""Exercise the public shared-memory walkthrough with a synthetic account.

Requires the published remembr==0.2.1 SDK and a ready, disposable local server.
Account/project metadata remains. Credentials are never printed or saved.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import secrets
import subprocess
import time
from importlib.metadata import version
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()
    base = os.getenv("REMEMBR_URL", "http://localhost:8000").rstrip("/")
    if args.recreate and os.getenv("COMPOSE_PROJECT_NAME") != "remembr_ci_default":
        raise RuntimeError("Container recreation is restricted to remembr_ci_default")
    assert version("remembr") == "0.2.1", "Install the published remembr==0.2.1 SDK"

    def call(method, path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        request = Request(
            base + "/api/v1" + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        with urlopen(request, timeout=60) as response:
            return json.load(response)["data"]

    identity = {
        "email": "onboarding-" + secrets.token_hex(12) + "@example.com",
        "password": secrets.token_urlsafe(24),
        "org_name": "Synthetic onboarding acceptance",
    }
    registered = call("POST", "/auth/register", identity)
    owner = call(
        "POST", "/auth/login", {k: identity[k] for k in ("email", "password")}
    )["access_token"]
    assert registered["access_token"]

    def admin(method, path, body=None):
        return call(method, "/projects" + path, body, owner)

    project = admin("POST", "", {"name": "Onboarding acceptance"})
    space = admin("POST", f"/{project['id']}/spaces", {"name": "Decisions"})
    principal = admin("POST", "/principals", {"name": "First agent"})
    namespace = {}
    try:
        admin(
            "PUT",
            f"/spaces/{space['id']}/grants/{principal['id']}",
            {"can_read": True, "can_write": True},
        )
        os.environ.update(
            REMEMBR_API_KEY=principal["api_key"],
            REMEMBR_SPACE_ID=space["id"],
            REMEMBR_URL=base,
        )
        guide = (ROOT / "docs/getting-started.md").read_text(encoding="utf-8")
        (example,) = re.findall(r"```python\n(.*?)\n```", guide, re.DOTALL)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(example, "docs/getting-started.md", "exec"), namespace)
        client, saved = namespace["client"], namespace["saved"]
        assert saved["author_id"] == principal["id"]
        if args.recreate:
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
            deadline = time.monotonic() + 180
            while True:
                try:
                    if call("GET", "/ready")["status"] == "ready":
                        break
                except (OSError, ValueError):
                    pass
                if time.monotonic() > deadline:
                    raise TimeoutError("Recreated stack did not become ready")
                time.sleep(3)
        recalled = client.projects.search(
            space["id"], "Which database does the project use?", mode="hybrid"
        )
        assert recalled["results"][0]["id"] == saved["id"]
        assert recalled["results"][0]["content"] == saved["content"]
        print(
            json.dumps(
                {
                    "result": "passed",
                    "published_sdk": version("remembr"),
                    "registration_and_login": True,
                    "documented_example": True,
                    "authenticated_authorship": True,
                    "restart_recall": args.recreate,
                }
            )
        )
    finally:
        if "saved" in namespace:
            admin(
                "DELETE", f"/spaces/{space['id']}/memories/{namespace['saved']['id']}"
            )
        admin("DELETE", f"/principals/{principal['id']}")


if __name__ == "__main__":
    main()
